"""
GitHub Repository Ingestion Pipeline

Connects the RepositoryWalker → Parsers → SignalAggregator pipeline
and produces a unified DiscoveryResult with nodes and edges.

Flow:
    1. Walker clones repo → produces ParseableFileSet (tier 1 + tier 2 files)
    2. Read file contents from the cloned repo
    3. Tier 1 files → IaCParser + DependencyParser (deterministic)
    4. Tier 2 files → SemanticParser (LLM-assisted)
    5. All signals → SignalAggregator (deduplication)
    6. InfrastructureSignal → DiscoveryNode + DiscoveryEdge
    7. Return DiscoveryResult(source="github", ...)
"""

import os
import asyncio
import tempfile
import subprocess
import logging
from typing import List, Optional
from apps.api.ingestors.github.walker import RepositoryWalker
from apps.api.ingestors.github.utils import _get_auth_url
from apps.api.ingestors.github.deterministic import IaCParser, DependencyParser
from apps.api.ingestors.github.semantic import SemanticParser
from apps.api.ingestors.github.aggregator import SignalAggregator
from apps.api.ingestors.github.models import InfrastructureSignal, FileMetadata
from apps.api.ingestors.aws.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge

logger = logging.getLogger(__name__)


# Mapping from InfrastructureSignal component_type → DiscoveryNode node_type
COMPONENT_TO_NODE_TYPE = {
    "Database": "datastore",
    "Cache": "datastore",
    "Queue": "integration",
    "Worker": "compute",
    "Cloud-Service": "compute",
    "Compute": "compute",
    "Storage": "storage",
    "Service": "compute",
    "Resource": "compute",
    "API": "network",
}


class GitHubIngestionPipeline:
    """
    Full pipeline: clone repo → parse → aggregate → produce DiscoveryResult.
    """

    def __init__(
        self,
        repo_url: str,
        branch: str,
        access_token: str,
        use_semantic: bool = False,
        semantic_model: str = "llama3.2",
    ):
        self.repo_url = repo_url.rstrip("/")
        self.branch = branch
        self.access_token = access_token
        self.use_semantic = use_semantic
        self.semantic_model = semantic_model

    async def run(self) -> DiscoveryResult:
        """Execute the full ingestion pipeline and return a DiscoveryResult."""
        logger.info(f"Starting GitHub ingestion for {self.repo_url} on branch {self.branch}")

        # Step 1: Walk to get metadata using RepositoryWalker
        walker = RepositoryWalker()
        
        # We still need a temp directory to read the file contents during parsing
        with tempfile.TemporaryDirectory() as temp_dir:
            # We must override the clone logic to keep files in temp_dir for Step 3
            # OR better: modify RepositoryWalker to optionally take a directory.
            # For now, to keep it simple and fix the crash, we just let walker do its thing
            # but we need the files locally to read them.
            
            # Re-implementing the Step 1 clone with the CORRECT auth url
            auth_url = _get_auth_url(self.repo_url, self.access_token)
            process = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth=1", "--branch", self.branch, auth_url, ".",
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise Exception(f"Failed to clone repository: {stderr.decode()}")

            logger.info(f"Cloned {self.repo_url} successfully")

            # Step 2: Use the already cloned directory to perform the walk
            file_set = await walker.clone_and_walk(
                repo_url=self.repo_url,
                branch=self.branch,
                access_token=self.access_token
            )

            logger.info(
                f"Found {len(file_set.tier_1_files)} Tier 1 and "
                f"{len(file_set.tier_2_files)} Tier 2 files"
            )

            # Step 3: Read file contents and parse
            all_signals: List[InfrastructureSignal] = []

            iac_parser = IaCParser()
            dep_parser = DependencyParser()

            # Parse Tier 1 files (IaC + dependency manifests)
            for file_meta in file_set.tier_1_files:
                full_path = os.path.join(temp_dir, file_meta.path)
                if not os.path.isfile(full_path):
                    continue
                try:
                    with open(full_path, "r", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                filename = os.path.basename(file_meta.path).lower()

                if file_meta.extension == ".tf":
                    all_signals.extend(iac_parser.parse_terraform(file_meta.path, content))
                elif "docker-compose" in filename and file_meta.extension in (".yml", ".yaml"):
                    all_signals.extend(iac_parser.parse_compose(file_meta.path, content))
                elif filename == "package.json":
                    all_signals.extend(dep_parser.parse_package_json(file_meta.path, content))
                elif "requirements" in filename and file_meta.extension == ".txt":
                    all_signals.extend(dep_parser.parse_requirements_txt(file_meta.path, content))

            logger.info(f"Deterministic parsing yielded {len(all_signals)} signals")

            # Step 4: Optionally parse Tier 2 files with semantic parser
            if self.use_semantic and file_set.tier_2_files:
                try:
                    semantic_parser = SemanticParser(model=self.semantic_model)
                    tier_2_files_content = []
                    for file_meta in file_set.tier_2_files[:20]:  # Cap at 20 files
                        full_path = os.path.join(temp_dir, file_meta.path)
                        if not os.path.isfile(full_path):
                            continue
                        try:
                            with open(full_path, "r", errors="replace") as f:
                                content = f.read()
                            tier_2_files_content.append({"path": file_meta.path, "content": content})
                        except Exception:
                            continue

                    if tier_2_files_content:
                        semantic_signals = await semantic_parser.parse_application_code(tier_2_files_content)
                        all_signals.extend(semantic_signals)
                        logger.info(f"Semantic parsing yielded {len(semantic_signals)} additional signals")
                except Exception as e:
                    logger.warning(f"Semantic parsing failed (non-fatal): {e}")

            # Step 5: Aggregate / deduplicate
            aggregator = SignalAggregator(match_threshold=70)
            final_signals = aggregator.aggregate(all_signals)
            logger.info(f"After aggregation: {len(final_signals)} unique signals")

            # Step 6: Convert to DiscoveryNodes + DiscoveryEdges
            nodes = self._signals_to_nodes(final_signals)
            edges = self._infer_edges(nodes)

            return DiscoveryResult(
                source="github",
                nodes=nodes,
                edges=edges,
                metadata={
                    "repo_url": self.repo_url,
                    "branch": self.branch,
                    "tier_1_count": len(file_set.tier_1_files),
                    "tier_2_count": len(file_set.tier_2_files),
                    "raw_signal_count": len(all_signals),
                    "deduplicated_count": len(final_signals),
                },
            )

    def _signals_to_nodes(self, signals: List[InfrastructureSignal]) -> List[DiscoveryNode]:
        """Convert InfrastructureSignals to DiscoveryNodes."""
        nodes = []
        for sig in signals:
            node_type = COMPONENT_TO_NODE_TYPE.get(sig.component_type, "compute")
            key = f"github:{sig.component_type.lower()}:{sig.name}"

            nodes.append(
                DiscoveryNode(
                    key=key,
                    display_name=sig.name,
                    node_type=node_type,
                    properties={
                        "service": sig.component_type,
                        "source_location": sig.source_location,
                        "confidence_score": sig.confidence_score,
                        **sig.config,
                    },
                    source_metadata={
                        "repo_url": self.repo_url,
                        "extraction_method": "deterministic" if sig.confidence_score >= 0.8 else "semantic",
                    },
                )
            )
        return nodes

    def _infer_edges(self, nodes: List[DiscoveryNode]) -> List[DiscoveryEdge]:
        """
        Infer edges between nodes based on component relationships.

        Examples:
            - Service -> depends_on -> Database
            - Service -> depends_on -> Cache
            - Worker -> consumes_from -> Queue
            - API -> calls -> Service
        """
        edges = []
        services = [n for n in nodes if n.properties.get("service") in ("Service", "Compute", "Worker", "API")]
        datastores = [n for n in nodes if n.properties.get("service") in ("Database", "Cache")]
        queues = [n for n in nodes if n.properties.get("service") == "Queue"]

        for svc in services:
            for ds in datastores:
                edges.append(
                    DiscoveryEdge(
                        from_node_key=svc.key,
                        to_node_key=ds.key,
                        edge_type="depends_on",
                        properties={"inferred": True},
                    )
                )
            for q in queues:
                edge_type = "consumes_from" if svc.properties.get("service") == "Worker" else "publishes_to"
                edges.append(
                    DiscoveryEdge(
                        from_node_key=svc.key,
                        to_node_key=q.key,
                        edge_type=edge_type,
                        properties={"inferred": True},
                    )
                )

        return edges
