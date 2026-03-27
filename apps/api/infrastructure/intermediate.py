import logging
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, text
from apps.api.database import engine
from apps.api.models import Node, Edge, NodeType, EdgeType, Graph
from apps.api.infrastructure.processor.pipeline import InfrastructurePipeline
from apps.api.ingestors.aws.schemas import DiscoveryResult

logger = logging.getLogger(__name__)

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

async def ingest_to_graph(client_id: str, results: List[DiscoveryResult], session: Optional[Session] = None):
    """
    Main entry point for discovery-to-graph ingestion.
    Runs the modular IR pipeline and saves the results to the specified client's graph.
    """
    client_id_str = str(client_id)
    
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
        # Get or Create Graph for this client
        graph = _session.exec(
            select(Graph).where(Graph.client_id == client_id_str, Graph.name == "Infrastructure Design")
        ).first()
        
        if not graph:
            print(f"DEBUG: Creating 'Infrastructure Design' graph for {client_id_str}")
            graph = Graph(
                client_id=client_id_str,
                name="Infrastructure Design",
                description="Automatically generated infrastructure map"
            )
            _session.add(graph)
            _session.commit()
            _session.refresh(graph)
        
        graph_id = graph.id
        
        # 4. Get/Create NodeType and EdgeType
        node_type = _session.exec(select(NodeType).where(NodeType.graph_id == graph_id, NodeType.name == "Infrastructure")).first()
        if not node_type:
            node_type = NodeType(client_id=client_id_str, graph_id=graph_id, name="Infrastructure", category="Infrastructure")
            _session.add(node_type)
            _session.commit()
            _session.refresh(node_type)
            
        edge_type = _session.exec(select(EdgeType).where(EdgeType.graph_id == graph_id, EdgeType.name == "connects")).first()
        if not edge_type:
            edge_type = EdgeType(client_id=client_id_str, graph_id=graph_id, name="connects")
            _session.add(edge_type)
            _session.commit()
            _session.refresh(edge_type)

        # 5. Clear existing nodes and edges for this graph
        _session.exec(text(f"DELETE FROM edge WHERE graph_id = '{graph_id}'"))
        _session.exec(text(f"DELETE FROM node WHERE graph_id = '{graph_id}'"))
        _session.commit()

        # 6. Create Nodes and Edges
        node_key_to_id = {}
        from dataclasses import asdict
        
        for ir_node in context.nodes.values():
            properties = {
                "template_id": ir_node.template_id,
                "environment": ir_node.environment,
                "confidence": ir_node.confidence,
                "source_completeness": ir_node.source_completeness,
                "validation_warnings": [asdict(w) for w in ir_node.validation_warnings] if hasattr(ir_node, 'validation_warnings') else [],
                **ir_node.properties
            }
            db_node = Node(
                client_id=client_id_str,
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
                    client_id=client_id_str,
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
        logger.info(f"Ingested {len(context.nodes)} nodes and {len(context.edges)} potential edges to Graph {graph_id} for client {client_id_str}")
        print(f"DEBUG: Successfully ingested {len(context.nodes)} nodes to Graph {graph_id}")
        
    except Exception as e:
        _session.rollback()
        logger.error(f"Post-discovery ingestion failed for client {client_id_str}: {e}")
        print(f"ERROR: Ingestion failed: {e}")
        raise
    finally:
        # Only close if we created it
        if session is None:
            _session.close()
