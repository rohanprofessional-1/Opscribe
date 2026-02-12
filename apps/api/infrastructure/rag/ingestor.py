from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from apps.api.models import ArchitectureGraph, Node, Edge
from apps.api.infrastructure.rag.models import KnowledgeBaseItem
from apps.api.infrastructure.rag.embeddings import EmbeddingService

class GraphIngestor:
    def __init__(self, session: Session):
        self.session = session
        self.embedding_service = EmbeddingService()

    def ingest_graph(self, graph_id: UUID):
        # 1. Fetch Graph Data
        graph = self.session.get(ArchitectureGraph, graph_id)
        if not graph:
            raise ValueError(f"Graph with ID {graph_id} not found")

        # 2. Process Nodes
        for node in graph.nodes:
            self._process_node(node, graph.tenant_id)

        # 3. Process Edges
        for edge in graph.edges:
            self._process_edge(edge, graph.tenant_id)
            
        self.session.commit()

    def _process_node(self, node: Node, tenant_id: UUID):
        # Create text representation of the node
        text_content = f"Component: {node.label} ({node.type}). "
        if node.data:
            text_content += f"Configuration: {node.data}. "
        
        # Generate embedding
        embedding = self.embedding_service.generate_embedding(text_content)

        # Create/Update KnowledgeBaseItem
        # Check if exists to update or create new (simplified for now: always create/append)
        # ideally we should dedup or update existing items
        
        item = KnowledgeBaseItem(
            tenant_id=tenant_id,
            graph_id=node.graph_id,
            entity_id=node.id,
            content=text_content,
            embedding=embedding,
            metadata={"type": "node", "node_type": node.type},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self.session.add(item)

    def _process_edge(self, edge: Edge, tenant_id: UUID):
        # We need to fetch source and target node labels for context
        source = self.session.get(Node, edge.source_id)
        target = self.session.get(Node, edge.target_id)
        
        if not source or not target:
            return

        text_content = f"Connection: {source.label} interacts with {target.label}. "
        text_content += f"Type: {edge.type}. "
        if edge.data:
            text_content += f"Details: {edge.data}."

        embedding = self.embedding_service.generate_embedding(text_content)

        item = KnowledgeBaseItem(
            tenant_id=tenant_id,
            graph_id=edge.graph_id,
            entity_id=edge.id,
            content=text_content,
            embedding=embedding,
            metadata={"type": "edge", "relation": edge.type},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self.session.add(item)
