import os
import asyncio
import tempfile
import fnmatch
import subprocess
from typing import List, Tuple, Optional
from pathlib import Path

from apps.api.ingestors.github.models import FileMetadata, ParseableFileSet
from apps.api.ingestors.github.utils import _get_auth_url

class RepositoryWalker:
    async def _run_command(self, *args, cwd: Optional[str] = None) -> Tuple[str, str, int]:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode('utf-8', errors='replace').strip(), stderr.decode('utf-8', errors='replace').strip(), process.returncode or 0

    async def _get_last_commit_sha(self, repo_dir: str, file_path: str) -> str:
        stdout, _, _ = await self._run_command("git", "log", "-n", "1", "--pretty=format:%H", "--", file_path, cwd=repo_dir)
        return stdout

    def _is_tier_1(self, filename: str) -> bool:
        patterns = [
            "Dockerfile", "docker-compose*.yml", "*.tf", "*.bicep",
            "*.yaml", "*.yml", "*requirements*.txt", "package.json", "pyproject.toml"
        ]
        return any(fnmatch.fnmatch(filename, p) for p in patterns)

    def _is_tier_2(self, rel_path: str, filename: str) -> bool:
        doc_patterns = ["*.py", "*.ts", "*.go", "*.java"]
        if not any(fnmatch.fnmatch(filename, p) for p in doc_patterns):
            return False
            
        if os.path.dirname(rel_path) == "":
            return True
            
        allowed_dirs = {"infra", "deploy", "config", "src"}
        parts = Path(rel_path).parts
        if parts and parts[0] in allowed_dirs:
            return True
            
        return False

    def _is_tier_3(self, rel_path: str) -> bool:
        """Tier 3: Skip defaults (modules, git internals, tests, lockfiles)"""
        skip_dirs = {".git", "node_modules", "venv", "__pycache__", ".venv"}
        parts = Path(rel_path).parts
        if any(d in skip_dirs for d in parts):
            return True
            
        path_lower = str(rel_path).lower()
        if "test" in path_lower:
            return True
        if "lock" in path_lower:
            return True
            
        return False

    async def clone_and_walk(self, repo_url: str, branch: str, access_token: str) -> ParseableFileSet:
        auth_url = _get_auth_url(repo_url, access_token)
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout, stderr, rc = await self._run_command(
                "git", "clone", "--depth=1", "--branch", branch, auth_url, ".", 
                cwd=temp_dir
            )
            if rc != 0:
                raise Exception(f"Failed to clone repository: {stderr}")

            tier_1_files: List[FileMetadata] = []
            tier_2_files: List[FileMetadata] = []
            
            # Tasks for fetching SHAs concurrently to speed up the loop
            sha_tasks = []
            metadata_placeholders = []

            for root, _, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, temp_dir)
                    
                    if self._is_tier_3(rel_path):
                        continue

                    is_t1 = self._is_tier_1(file)
                    is_t2 = False if is_t1 else self._is_tier_2(rel_path, file)

                    if is_t1 or is_t2:
                        size = os.path.getsize(full_path)
                        ext = "".join(Path(file).suffixes) if Path(file).suffixes else ""
                        
                        placeholder = {
                            "path": rel_path,
                            "extension": ext,
                            "size_bytes": size,
                            "is_t1": is_t1
                        }
                        metadata_placeholders.append(placeholder)
                        sha_tasks.append(self._get_last_commit_sha(temp_dir, rel_path))

            # Fetch all SHAs concurrently
            shas = await asyncio.gather(*sha_tasks)

            for placeholder, sha in zip(metadata_placeholders, shas):
                meta = FileMetadata(
                    path=placeholder["path"],
                    extension=placeholder["extension"],
                    size_bytes=placeholder["size_bytes"],
                    last_commit_sha=sha
                )
                if placeholder["is_t1"]:
                    tier_1_files.append(meta)
                else:
                    tier_2_files.append(meta)

            return ParseableFileSet(tier_1_files=tier_1_files, tier_2_files=tier_2_files)
