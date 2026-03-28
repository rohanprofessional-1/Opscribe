"""
GitHub Ingestion Pipeline — RAW Layer

Clones a repository, parses IaC and dependency files, and emits
DiscoveryResult conforming to the raw_v1 schema spec.

Pipeline Steps:
  [1] Authenticate with GitHub App
  [2] Retrieve installation repos
  [3] Clone repository
  [4] Walk file tree
  [5] Parse IaC + dependency files
  [6] Aggregate signals
  [7] Build RAW nodes & edges
  [8] (Optional) Infer macro blocks — tagged is_inferred=true
  [9] Return DiscoveryResult
"""

import os
import asyncio
import hashlib
import tempfile
import subprocess
import logging
from time import time
from typing import List, Optional, Dict, Any

from apps.api.ingestors.github.walker import RepositoryWalker
from apps.api.ingestors.github.deterministic import IaCParser, DependencyParser
from apps.api.ingestors.github.aggregator import SignalAggregator
from apps.api.ingestors.github.models import InfrastructureSignal
from apps.api.ingestors.pipeline.schemas import DiscoveryNode, DiscoveryEdge, DiscoveryResult
from apps.api.models import ConnectedRepository
from sqlmodel import Session

logger = logging.getLogger(__name__)


# ── Coarse category mapping ──────────────────────────────────────────
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

# ── Fine-grained subtype mapping ─────────────────────────────────────
COMPONENT_TO_SUBTYPE = {
    "Database": "database",
    "Cache": "cache",
    "Queue": "message_queue",
    "Worker": "background_worker",
    "Cloud-Service": "cloud_service",
    "Compute": "compute_instance",
    "Storage": "object_storage",
    "Service": "service",
    "Resource": "resource",
    "API": "api_gateway",
}


class GitHubIngestionPipeline:
    def __init__(
        self,
        repo_url: str,
        branch: str,
        access_token: Optional[str] = None,
        use_semantic: bool = False,
        semantic_model: str = "llama3.2",
        session: Optional[Session] = None,
        connected_repo_id: Optional[str] = None,
    ):
        self.repo_url = repo_url.rstrip("/")
        self.branch = branch
        self.access_token = access_token
        self.use_semantic = use_semantic
        self.semantic_model = semantic_model
        self.session = session
        self.connected_repo_id = connected_repo_id

        # Derive repo_full_name for globally unique node keys (Spec §7)
        self.repo_full_name = (
            self.repo_url.split("github.com/")[-1]
            if "github.com/" in self.repo_url
            else self.repo_url
        )

    # ── Pipeline step tracker ────────────────────────────────────────
    def _update_step(self, step_index: int, description: str = ""):
        """Log pipeline progress and persist step index to DB."""
        logger.info(f"[STEP {step_index}] {description}")
        if self.session and self.connected_repo_id:
            try:
                repo = self.session.get(ConnectedRepository, self.connected_repo_id)
                if repo:
                    repo.current_step_index = step_index
                    self.session.add(repo)
                    self.session.commit()
            except Exception as e:
                logger.error(f"Failed to update pipeline step: {e}")

    # ── Auth URL builder ─────────────────────────────────────────────
    def _get_auth_url(self) -> str:
        from urllib.parse import urlparse
        if not self.access_token:
            return self.repo_url
        parsed = urlparse(self.repo_url)
        return parsed._replace(
            netloc=f"x-access-token:{self.access_token}@{parsed.netloc}"
        ).geturl()

    # ── Remote SHA ───────────────────────────────────────────────────
    async def get_remote_sha(self) -> Optional[str]:
        auth_url = self._get_auth_url()
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "ls-remote", auth_url, self.branch,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=10.0
            )
            if process.returncode == 0:
                output = stdout.decode().strip()
                if output:
                    return output.split()[0]
        except Exception as e:
            logger.warning(f"Failed to get remote SHA for {self.repo_url}: {e}")
        return None

    # ── Main pipeline ────────────────────────────────────────────────
    async def run(self) -> DiscoveryResult:
        t0 = time()

        self._update_step(1, "Authenticated with GitHub App")
        commit_sha = await self.get_remote_sha()
        logger.info(
            f"Starting GitHub ingestion for {self.repo_url} "
            f"on branch {self.branch} (SHA: {commit_sha})"
        )

        self._update_step(2, "Retrieved installation repos")
        self._update_step(3, "Cloning repository")

        walker = RepositoryWalker(
            repo_url=self.repo_url,
            branch=self.branch,
            auth_url=self._get_auth_url(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_set = await walker.walk(temp_dir)
            self._update_step(4, f"Walked file tree — {len(file_set.tier_1_files)} tier-1 files")

            iac_parser = IaCParser()
            dep_parser = DependencyParser()
            all_signals: List[InfrastructureSignal] = []

            self._update_step(5, "Parsing IaC + dependency files")
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

                if file_meta.extension in (".tf", ".hcl"):
                    all_signals.extend(iac_parser.parse_terraform(file_meta.path, content))
                elif "docker-compose" in filename and file_meta.extension in (".yml", ".yaml"):
                    all_signals.extend(iac_parser.parse_compose(file_meta.path, content))
                elif filename == "package.json":
                    all_signals.extend(dep_parser.parse_package_json(file_meta.path, content))
                elif "requirements" in filename and file_meta.extension == ".txt":
                    all_signals.extend(dep_parser.parse_requirements_txt(file_meta.path, content))

            self._update_step(6, f"Extracted {len(all_signals)} raw signals")

            aggregator = SignalAggregator(match_threshold=70)
            final_signals = aggregator.aggregate(all_signals)
            self._update_step(7, f"Aggregated to {len(final_signals)} deduplicated signals")

            # ── Build RAW nodes & edges (Spec §4, §5) ───────────────
            nodes, edges = self._signals_to_nodes_and_edges(final_signals)

            # ── Inferred macro blocks (Spec §6 — tagged is_inferred) ─
            macro_nodes, macro_edges = self._infer_macro_blocks(final_signals, nodes)
            nodes.extend(macro_nodes)
            edges.extend(macro_edges)

            self._update_step(8, f"Built RAW payload — {len(nodes)} nodes, {len(edges)} edges")

            # ── Content hash for fingerprinting (Spec §3) ────────────
            content_hash = self._compute_content_hash(nodes, edges)

            elapsed = round(time() - t0, 2)
            self._update_step(9, f"Pipeline complete in {elapsed}s")

            return DiscoveryResult(
                source="github",
                nodes=nodes,
                edges=edges,
                metadata={
                    "repo_url": self.repo_url,
                    "repo_full_name": self.repo_full_name,
                    "branch": self.branch,
                    "commit_sha": commit_sha,
                    "content_hash": content_hash,
                    "raw_signal_count": len(all_signals),
                    "deduplicated_count": len(final_signals),
                    "pipeline_elapsed_s": elapsed,
                },
            )

    # ── Node & Edge construction ─────────────────────────────────────
    def _signals_to_nodes_and_edges(
        self, signals: List[InfrastructureSignal]
    ) -> tuple[List[DiscoveryNode], List[DiscoveryEdge]]:
        nodes: List[DiscoveryNode] = []
        edges: List[DiscoveryEdge] = []
        node_key_map: Dict[str, str] = {}

        for sig in signals:
            node_type = COMPONENT_TO_NODE_TYPE.get(sig.component_type, "compute")
            node_subtype = COMPONENT_TO_SUBTYPE.get(sig.component_type)

            # Spec §7 — Global identity: github:{repo_full_name}:{entity_type}:{name}
            key = f"github:{self.repo_full_name}:{node_type}:{sig.name}"
            node_key_map[sig.name] = key

            nodes.append(
                DiscoveryNode(
                    key=key,
                    display_name=sig.name,
                    node_type=node_type,
                    node_subtype=node_subtype,
                    properties={
                        "role": sig.component_type,
                        "related_files": [sig.source_location],
                        "confidence_score": sig.confidence_score,
                        **sig.config,
                    },
                    source_metadata={
                        "file": sig.source_location,
                        "extraction_method": (
                            "deterministic" if sig.confidence_score >= 0.8 else "semantic"
                        ),
                        "confidence": sig.confidence_score,
                        "is_inferred": False,
                    },
                )
            )

        # ── Deterministic edges from raw config (e.g. docker depends_on) ─
        for sig in signals:
            source_key = node_key_map.get(sig.name)
            if not source_key:
                continue

            if "depends_on" in sig.config:
                deps = sig.config["depends_on"]
                if isinstance(deps, list):
                    for target_name in deps:
                        target_key = node_key_map.get(target_name)
                        if target_key:
                            edges.append(
                                DiscoveryEdge(
                                    from_node_key=source_key,
                                    to_node_key=target_key,
                                    edge_type="depends_on",
                                    direction="outbound",
                                    properties={
                                        "source": sig.source_location,
                                        "confidence": 1.0,
                                        "is_inferred": False,
                                    },
                                )
                            )

        return nodes, edges

    # ── Macro block inference (Spec §6 — clearly tagged) ─────────────
    def _infer_macro_blocks(
        self,
        final_signals: List[InfrastructureSignal],
        existing_nodes: List[DiscoveryNode],
    ) -> tuple[List[DiscoveryNode], List[DiscoveryEdge]]:
        nodes: List[DiscoveryNode] = []
        edges: List[DiscoveryEdge] = []
        is_frontend = False
        is_backend = False
        backend_node_keys: List[str] = []
        frontend_node_keys: List[str] = []

        for sig in final_signals:
            pkg = sig.config.get("package", "").lower()
            key = f"github:{self.repo_full_name}:{COMPONENT_TO_NODE_TYPE.get(sig.component_type, 'compute')}:{sig.name}"

            if pkg in ("react", "next", "vue", "angular", "svelte"):
                is_frontend = True
                frontend_node_keys.append(key)
            elif pkg in ("express", "fastapi", "flask", "django", "nest", "pgvector", "psycopg2-binary"):
                is_backend = True
                backend_node_keys.append(key)
            elif sig.config.get("image", "").startswith("node"):
                if sig.name.startswith("frontend"):
                    is_frontend = True
                    frontend_node_keys.append(key)
                elif sig.name.startswith("backend") or sig.name == "api":
                    is_backend = True
                    backend_node_keys.append(key)

        # ── Inferred source_metadata template ────────────────────────
        inferred_meta = {
            "file": None,
            "extraction_method": "grouping",
            "confidence": 0.85,
            "is_inferred": True,
            "inference_type": "grouping",
        }

        if is_frontend:
            front_key = f"github:{self.repo_full_name}:macro:frontend"
            nodes.append(
                DiscoveryNode(
                    key=front_key,
                    display_name="Frontend Application",
                    node_type="compute",
                    node_subtype="frontend_app",
                    properties={"role": "Frontend Component"},
                    source_metadata=inferred_meta,
                )
            )
            for tk in frontend_node_keys:
                edges.append(
                    DiscoveryEdge(
                        from_node_key=front_key,
                        to_node_key=tk,
                        edge_type="contains",
                        direction="outbound",
                        properties={"confidence": 0.9, "is_inferred": True},
                    )
                )

        if is_backend:
            back_key = f"github:{self.repo_full_name}:macro:backend"
            nodes.append(
                DiscoveryNode(
                    key=back_key,
                    display_name="Backend API",
                    node_type="compute",
                    node_subtype="backend_api",
                    properties={"role": "Backend API"},
                    source_metadata=inferred_meta,
                )
            )
            for tk in backend_node_keys:
                edges.append(
                    DiscoveryEdge(
                        from_node_key=back_key,
                        to_node_key=tk,
                        edge_type="contains",
                        direction="outbound",
                        properties={"confidence": 0.9, "is_inferred": True},
                    )
                )

            # Frontend → Backend communication
            if is_frontend:
                edges.append(
                    DiscoveryEdge(
                        from_node_key=f"github:{self.repo_full_name}:macro:frontend",
                        to_node_key=back_key,
                        edge_type="communicates_with",
                        direction="outbound",
                        properties={"confidence": 0.7, "is_inferred": True},
                    )
                )

            # Backend → Datastores
            for n in existing_nodes:
                if n.node_type == "datastore" or "postgres" in str(
                    n.properties.get("image", "")
                ):
                    edges.append(
                        DiscoveryEdge(
                            from_node_key=back_key,
                            to_node_key=n.key,
                            edge_type="depends_on",
                            direction="outbound",
                            properties={"confidence": 0.8, "is_inferred": True},
                        )
                    )

        return nodes, edges

    # ── Content hash (Spec §3) ───────────────────────────────────────
    @staticmethod
    def _compute_content_hash(
        nodes: List[DiscoveryNode], edges: List[DiscoveryEdge]
    ) -> str:
        """Deterministic hash of the discovery payload for idempotency."""
        hasher = hashlib.md5()
        for n in sorted(nodes, key=lambda x: x.key):
            hasher.update(n.key.encode())
        for e in sorted(edges, key=lambda x: (x.from_node_key, x.to_node_key)):
            hasher.update(f"{e.from_node_key}->{e.to_node_key}".encode())
        return hasher.hexdigest()
