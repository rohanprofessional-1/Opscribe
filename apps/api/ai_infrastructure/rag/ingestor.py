import logging
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select, delete
from apps.api.models import Graph, Node, Edge
from apps.api.ai_infrastructure.rag.models import KnowledgeBaseItem
from apps.api.ai_infrastructure.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class GraphIngestor:
    def __init__(self, session: Session):
        self.session = session
        self.embedding_service = EmbeddingService()
        # UI-specific properties that should be ignored to avoid confusing the LLM with 'screen placement' data
        self.ignored_props = {
            "position", "x", "y", "icon", "color", "categoryColor", "bg", 
            "width", "height", "selected", "dragging", "z", "zIndex"
        }

    def ingest_graph(self, graph_id: UUID):
        # 1. Fetch Graph Data
        graph = self.session.get(Graph, graph_id)
        if not graph:
            raise ValueError(f"Graph with ID {graph_id} not found")

        # 2. Purge stale embeddings for this graph (deduplication)
        self.session.exec(
            delete(KnowledgeBaseItem).where(KnowledgeBaseItem.graph_id == graph_id)
        )
        logger.info(f"Purged existing embeddings for graph {graph_id}")

        # 2. Process Nodes
        for node in graph.nodes:
            self._process_node(node, graph.client_id)

        # 3. Process Edges
        for edge in graph.edges:
            self._process_edge(edge, graph.client_id)
            
        self.session.commit()

    def _process_node(self, node: Node, tenant_id: UUID):
        # 1. Filter out UI noise from properties
        filtered_props = {}
        if node.properties:
            filtered_props = {k: v for k, v in node.properties.items() if k not in self.ignored_props}
        
        # 2. Extract type and name
        node_type_name = node.node_type.name if node.node_type else "Infrastructure"
        category = filtered_props.get("category", node_type_name)
        display = node.display_name or node.key

        # 3. Create a narrative representation for the 'Architectural Advisor' persona
        # We focus on what the component IS and DOES rather than its raw JSON.
        text_content = f"Architecture Component: '{display}' is a {category} node. "
        
        if filtered_props:
            # Format properties into human-readable details
            details = ", ".join([f"{k}: {v}" for k, v in filtered_props.items() if k != "category" and k != "label"])
            if details:
                text_content += f"Its specific technical configurations include: {details}. "
        
        # 4. Generate embedding for semantic search
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
            metadata_={"type": "node", "node_type": node_type_name, "node_key": node.key},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self.session.add(item)

    def _process_edge(self, edge: Edge, tenant_id: UUID):
        # We need to fetch source and target node labels for context
        source = self.session.get(Node, edge.from_node_id)
        target = self.session.get(Node, edge.to_node_id)
        
        if not source or not target:
            return

        source_display = source.display_name or source.key
        target_display = target.display_name or target.key
        edge_type_name = edge.edge_type.name if edge.edge_type else "connectivity"

        # Narrative template for relationships to help LLM infer dependencies
        text_content = f"Architecture Connectivity: The component '{source_display}' facilitates a '{edge_type_name}' relationship with '{target_display}'. "
        
        if edge.properties:
            # Filter edge properties too
            filtered_edge_props = {k: v for k, v in edge.properties.items() if k not in self.ignored_props}
            if filtered_edge_props:
                text_content += f"Connection details: {filtered_edge_props}."

        embedding = self.embedding_service.generate_embedding(text_content)

        item = KnowledgeBaseItem(
            tenant_id=tenant_id,
            graph_id=edge.graph_id,
            entity_id=edge.id,
            content=text_content,
            embedding=embedding,
            metadata_={"type": "edge", "relation": edge_type_name},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self.session.add(item)
