import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlmodel import Session, select
import os
import shutil

from apps.api.models import Node, Edge, ConnectedRepository, Client
from apps.api.infrastructure.rag.models import KnowledgeBaseItem
from apps.api.ingestors.github.client import GitHubClient
from apps.api.ingestors.github.deterministic import IaCParser, DependencyParser
from apps.api.ingestors.github.semantic import SemanticParser
from apps.api.ingestors.github.app_auth import get_installation_token
from apps.api.infrastructure.rag.embeddings import EmbeddingService
from apps.api.ingestors.github.pipeline import COMPONENT_TO_NODE_TYPE
from apps.api.models import Graph, NodeType, EdgeType
import datetime

logger = logging.getLogger(__name__)

class IncrementalUpdater:
    def __init__(self, session: Session, tenant_id: str, repo_url: str, installation_id: str):
        self.session = session
        self.tenant_id = UUID(tenant_id)
        self.repo_url = repo_url
        self.installation_id = installation_id
        
        parts = self.repo_url.rstrip("/").split("/")
        self.owner = parts[-2]
        self.repo = parts[-1]
        
        self.embedding_service = EmbeddingService()
        self.iac_parser = IaCParser()
        self.dep_parser = DependencyParser()
        self.semantic_parser = SemanticParser(model="llama3.2")

    async def _get_github_client(self) -> GitHubClient:
        token = await get_installation_token(self.installation_id)
        return GitHubClient(access_token=token)

    async def update_from_pr(self, pull_number: int, branch_ref: str):
        """Processes a PR by reading the changed files and updating the graph & vector databases incrementally."""
        gh_client = await self._get_github_client()
        
        logger.info(f"Fetching incrementally changed files for PR #{pull_number}")
        changed_files = await gh_client.get_pull_request_files(self.owner, self.repo, pull_number)
        
        modified_files = []
        deleted_files = []
        
        for f in changed_files:
            status = f.get("status")
            filename = f.get("filename")
            if status in ("added", "modified", "renamed"):
                modified_files.append(filename)
            elif status == "removed":
                deleted_files.append(filename)
                
        all_affected = modified_files + deleted_files
        
        if not all_affected:
            logger.info("No files affected in this PR.")
            return

        # Purge stale nodes/edges and vector chunks for ALL affected files
        self._purge_stale_data(all_affected)
        
        # Extract contents for the newly modified files
        new_signals = []
        tier_2_files_content: List[Dict[str, str]] = []
        
        for filename in modified_files:
            file_content = await gh_client.get_file_content(self.owner, self.repo, filename, branch_ref)
            if not file_content:
                continue
                
            # Chunk and Embed for Vector DB (RAG)
            self._ingest_file_to_vector_db(filename, file_content)
                
            # Parse for Graph DB (Nodes / Edges)
            fname_lower = filename.lower()
            if filename.endswith(".tf"):
                new_signals.extend(self.iac_parser.parse_terraform(filename, file_content))
            elif "docker-compose" in fname_lower and (filename.endswith(".yml") or filename.endswith(".yaml")):
                new_signals.extend(self.iac_parser.parse_compose(filename, file_content))
            elif "package.json" in fname_lower:
                new_signals.extend(self.dep_parser.parse_package_json(filename, file_content))
            elif "requirements" in fname_lower and filename.endswith(".txt"):
                new_signals.extend(self.dep_parser.parse_requirements_txt(filename, file_content))
            elif filename.endswith(('.py', '.js', '.ts', '.go', '.java')):
                tier_2_files_content.append({"path": filename, "content": file_content})
                
        # Semantic mapping
        if tier_2_files_content:
            logger.info(f"Running semantic parser on {len(tier_2_files_content)} tier 2 files")
            try:
                # Bypass Pyre list slice typing limitation
                subset = [tier_2_files_content[i] for i in range(min(20, len(tier_2_files_content)))]
                semantic_signals = await self.semantic_parser.parse_application_code(subset)
                new_signals.extend(semantic_signals)
            except Exception as e:
                logger.warning(f"Semantic parsing failed (non-fatal): {e}")
                
        # Insert newly mapped Graph DB nodes
        self._insert_graph_data(new_signals)
        
        # Commit all transactions
        self.session.commit()
        logger.info(f"Incremental update complete for PR #{pull_number}.")

    def _purge_stale_data(self, filenames: List[str]):
        """Deletes any Graph Nodes or Vector Chunks associated with the given filenames."""
        # Find Graph ID for this client (for simplicity, we assume one graph or pull the first)
        graph = self.session.exec(select(Graph).where(Graph.client_id == self.tenant_id)).first()
        graph_id_str = str(graph.id) if graph else ""
        
        # Purge Vector DB chunks
        kb_statement = select(KnowledgeBaseItem).where(KnowledgeBaseItem.tenant_id == self.tenant_id)
        kb_items = self.session.exec(kb_statement).all()
        for item in kb_items:
            path = item.metadata_.get("file_path", "")
            if path in filenames:
                self.session.delete(item)

        # Purge Graph DB Nodes
        node_stmt = select(Node).where(
            Node.client_id == self.tenant_id,
            Node.source == "github"
        )
        nodes = self.session.exec(node_stmt).all()
        for node in nodes:
            loc = node.properties.get("source_location", "")
            if any(f in loc for f in filenames):
                self.session.delete(node)

    def _ingest_file_to_vector_db(self, filename: str, content: str):
        """Chunks and embeds file content incrementally."""
        max_chunk_size = 3000
        overlap = 300
        
        chunks = []
        start = 0
        while start < len(content):
            end = start + max_chunk_size
            chunks.append(content[start:end]) # type: ignore
            start = end - overlap
            
        dummy_graph_id = self.tenant_id
        
        for i, chunk_text in enumerate(chunks):
            contextual_chunk = f"File: {filename}\n\n{chunk_text}"
            embedding = self.embedding_service.generate_embedding(contextual_chunk)
            
            item = KnowledgeBaseItem(
                tenant_id=self.tenant_id,
                graph_id=dummy_graph_id,
                entity_id=dummy_graph_id,
                content=contextual_chunk,
                embedding=embedding,
                metadata_={
                    "type": "repo_chunk",
                    "file_path": filename,
                    "chunk_index": i
                },
                created_at=datetime.datetime.utcnow().isoformat(),
                updated_at=datetime.datetime.utcnow().isoformat()
            )
            self.session.add(item)
            
    def _insert_graph_data(self, signals):
        """Converts signals to nodes and infers simple edges, then saves to DB."""
        if not signals:
            return
            
        graph = self.session.exec(select(Graph).where(Graph.client_id == self.tenant_id)).first()
        if not graph: return

        # Load/Create node types cache
        node_types_map = {}
        for nt in self.session.exec(select(NodeType).where(NodeType.graph_id == graph.id)).all():
            node_types_map[nt.name.lower()] = nt.id

        new_nodes = []
        for sig in signals:
            nt_name = COMPONENT_TO_NODE_TYPE.get(sig.component_type, "compute")
            
            if nt_name not in node_types_map:
                nt = NodeType(client_id=self.tenant_id, graph_id=graph.id, name=nt_name)
                self.session.add(nt)
                self.session.commit()
                self.session.refresh(nt)
                node_types_map[nt_name] = nt.id

            key = f"github:{sig.component_type.lower()}:{sig.name}"
            node = Node(
                client_id=self.tenant_id,
                graph_id=graph.id,
                node_type_id=node_types_map[nt_name],
                key=key,
                display_name=sig.name,
                source="github",
                properties={
                    "service": sig.component_type,
                    "source_location": sig.source_location,
                    "confidence_score": sig.confidence_score,
                    **sig.config,
                },
                source_metadata={
                    "repo_url": self.repo_url,
                    "extraction_method": "incremental"
                }
            )
            # Handle unique key constraint gracefully (upsert logic if needed, but since we purged, it relies on it)
            existing_node = self.session.exec(select(Node).where(Node.key == key, Node.graph_id == graph.id)).first()
            if not existing_node:
                self.session.add(node)
                new_nodes.append(node)

        self.session.commit()
        
        # Simple Inferred Edges
        edge_type_name = "depends_on"
        et = self.session.exec(select(EdgeType).where(EdgeType.graph_id == graph.id, EdgeType.name == edge_type_name)).first()
        if not et:
            et = EdgeType(client_id=self.tenant_id, graph_id=graph.id, name=edge_type_name)
            self.session.add(et)
            self.session.commit()
            self.session.refresh(et)
            
        # Services -> Databases
        services = [n for n in new_nodes if n.properties.get("service") in ("Service", "Compute", "Worker", "API")]
        datastores = [n for n in new_nodes if n.properties.get("service") in ("Database", "Cache")]
        
        for svc in services:
            for ds in datastores:
                edge = Edge(
                    client_id=self.tenant_id,
                    graph_id=graph.id,
                    edge_type_id=et.id,
                    from_node_id=svc.id,
                    to_node_id=ds.id,
                    properties={"inferred": True}
                )
                self.session.add(edge)
                
        self.session.commit()
