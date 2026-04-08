import logging
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, text
from apps.api.database import engine
from apps.api.models import Node, Edge, NodeType, EdgeType, Graph, Client
from apps.api.infrastructure.processor.pipeline import InfrastructurePipeline
from apps.api.ingestors.aws.schemas import DiscoveryResult
from apps.api.ai_infrastructure.rag.embedding_sync import re_embed_graph

logger = logging.getLogger(__name__)

async def ingest_to_all_clients(results: List[DiscoveryResult], original_client_id: str, graph_name: Optional[str] = None, session: Optional[Session] = None):
    """
    Wrapper to ingest discovery results for multiple clients.
    Updates the original client plus two hardcoded demo clients.
    """
    
    # Unique set of clients (to avoid double-ingesting if original is one of the demos)
    target_clients = list(set([original_client_id]))
    
    print(f"DEBUG: Triggering ingestion for clients: {target_clients}")
    
    for client_id in target_clients:
        try:
            # We use a fresh nested session or similar if provided, but ingest_to_graph handles its own session if None
            await ingest_to_graph(client_id=client_id, results=results, graph_name=graph_name, session=session)
        except Exception as e:
            logger.error(f"Failed to ingest for client {client_id}: {e}")
            print(f"ERROR: Failed ingestion for {client_id}: {e}")

async def ingest_to_graph(client_id: str | UUID, results: List[DiscoveryResult], graph_name: Optional[str] = None, session: Optional[Session] = None):
    """
    Main entry point for discovery-to-graph ingestion.
    Runs the modular IR pipeline and saves the results to the specified client's graph.
    """
    client_id_uuid = UUID(str(client_id)) if isinstance(client_id, str) else client_id
    target_graph_name = graph_name or "Infrastructure Design"
    
    # 1. Prepare raw data
    raw_github = {"sources": []}
    raw_aws = {"sources": []}
    
    for res in results:
        if res.source == "github":
            raw_github["sources"].append(_result_to_dict(res))
        elif res.source == "aws":
            raw_aws["sources"].append(_result_to_dict(res))
    
    # 2. Execute Infrastructure Pipeline
    pipeline = InfrastructurePipeline()
    context = pipeline.execute(raw_github, raw_aws)
    
    # 3. Persist to Database
    # Use provided session or create a new one
    _session = session
    if _session is None:
        _session = Session(engine)
    
    try:
        # Get or Create Graph for this client with the specified name
        graph = _session.exec(
            select(Graph).where(Graph.client_id == client_id_uuid, Graph.name == target_graph_name)
        ).first()
        
        if not graph:
             # Ensure the client exists before creating a graph for it
            client = _session.get(Client, client_id_uuid)
            if not client:
                logger.error(f"Cannot ingest for non-existent client {client_id_uuid}")
                return

            print(f"DEBUG: Creating '{target_graph_name}' graph for {client_id_uuid}")
            graph = Graph(
                client_id=client_id_uuid,
                name=target_graph_name,
                description=f"Automatically generated infrastructure map for {target_graph_name}"
            )
            _session.add(graph)
            _session.commit()
            _session.refresh(graph)
        
        graph_id = graph.id
        
        # 4. Get/Create NodeType and EdgeType
        node_type = _session.exec(select(NodeType).where(NodeType.graph_id == graph_id, NodeType.name == "Infrastructure")).first()
        if not node_type:
            node_type = NodeType(client_id=client_id_uuid, graph_id=graph_id, name="Infrastructure", category="Infrastructure")
            _session.add(node_type)
            _session.commit()
            _session.refresh(node_type)
            
        edge_type = _session.exec(select(EdgeType).where(EdgeType.graph_id == graph_id, EdgeType.name == "connects")).first()
        if not edge_type:
            edge_type = EdgeType(client_id=client_id_uuid, graph_id=graph_id, name="connects")
            _session.add(edge_type)
            _session.commit()
            _session.refresh(edge_type)

        # 5. Clear existing nodes and edges for this graph
        # Using bound parameters for security and type safety
        _session.exec(text("DELETE FROM edge WHERE graph_id = :gid").bindparams(gid=graph_id))
        _session.exec(text("DELETE FROM node WHERE graph_id = :gid").bindparams(gid=graph_id))
        _session.commit()

        # 6. Create Nodes and Edges
        node_key_to_id = {}
        from dataclasses import asdict
        
        for ir_node in context.nodes.values():
            properties = {
                "template_id": ir_node.template_id,
                "confidence": ir_node.confidence,
                "source_completeness": ir_node.source_completeness,
                "environment": ir_node.environment,
                "validation_warnings": [asdict(w) for w in ir_node.validation_warnings] if hasattr(ir_node, 'validation_warnings') else [],
                **ir_node.properties
            }
            db_node = Node(
                client_id=client_id_uuid,
                graph_id=graph_id,
                node_type_id=node_type.id,
                key=ir_node.id,
                display_name=ir_node.display_name,
                properties=properties,
                source=ir_node.source,
                source_metadata={"metadata": ir_node.source_metadata}
            )
            _session.add(db_node)
            _session.flush() # Get IDs without full commit
            node_key_to_id[ir_node.id] = db_node.id

        print(f"DEBUG: Mapping {len(context.edges)} edges for graph {graph_id}")
        for ir_edge in context.edges:
            from_id = node_key_to_id.get(ir_edge.from_node_id)
            to_id = node_key_to_id.get(ir_edge.to_node_id)
            if from_id and to_id:
                edge = Edge(
                    client_id=client_id_uuid,
                    graph_id=graph_id,
                    edge_type_id=edge_type.id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    properties={
                        "edge_type": ir_edge.edge_type,
                        "confidence": ir_edge.confidence,
                        "environment": ir_edge.environment,
                        **ir_edge.properties
                    }
                )
                _session.add(edge)
            else:
                print(f"DEBUG: Skipping edge {ir_edge.from_node_id} -> {ir_edge.to_node_id} (Nodes not found in mapping)")
        
        _session.commit()
        logger.info(f"Ingested {len(context.nodes)} nodes and {len(context.edges)} potential edges to Graph {graph_id} for client {client_id_uuid}")
        print(f"DEBUG: Successfully ingested {len(context.nodes)} nodes to Graph {graph_id}")

        # Post-commit cleanup: Re-embed the updated graph so the vector store stays in sync
        try:
            re_embed_graph(graph_id)
        except Exception as embed_e:
            logger.error(f"Post-ingestion embedding synchronization failed: {embed_e}")
        
    except Exception as e:
        _session.rollback()
        logger.error(f"Post-discovery ingestion failed for client {client_id_uuid}: {e}")
        print(f"ERROR: Ingestion failed: {e}")
        raise
    finally:
        # Only close if we created it
        if session is None:
            _session.close()

def _result_to_dict(result: DiscoveryResult) -> dict:
    """Serialize a DiscoveryResult to a JSON-serializable dict."""
    return {
        "source": result.source,
        "nodes": [
            {
                "key": n.key,
                "display_name": n.display_name,
                "node_type": n.node_type,
                "properties": n.properties,
                "source_metadata": n.source_metadata,
            }
            for n in result.nodes
        ],
        "edges": [
            {
                "from_node_key": e.from_node_key,
                "to_node_key": e.to_node_key,
                "edge_type": e.edge_type,
                "properties": e.properties,
            }
            for e in result.edges
        ],
        "metadata": result.metadata,
    }