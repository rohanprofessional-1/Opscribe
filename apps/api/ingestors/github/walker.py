import os
import asyncio
import subprocess
import logging
from typing import List, Optional
from pathlib import Path
from apps.api.ingestors.github.models import FileMetadata, ParseableFileSet

logger = logging.getLogger(__name__)

class RepositoryWalker:
    def __init__(self, repo_url: str, branch: str, auth_url: Optional[str] = None):
        self.repo_url = repo_url
        self.branch = branch
        self.auth_url = auth_url or repo_url

    async def _clone_repo(self, temp_dir: str):
        """Clone the repository into the specified directory."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth=1", "--branch", self.branch, self.auth_url, ".",
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60.0)
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"Git clone failed: {error_msg}")
                raise Exception(f"Failed to clone repository: {error_msg}")
            
            logger.info(f"Successfully cloned {self.repo_url} (branch: {self.branch}) to {temp_dir}")
        except asyncio.TimeoutError:
            logger.error(f"Git clone timed out for {self.repo_url}")
            raise Exception("Git clone timed out")

    async def walk(self, temp_dir: str) -> ParseableFileSet:
        """Walk the repository and categorize files."""
        await self._clone_repo(temp_dir)
        tier_1_files: List[FileMetadata] = []
        tier_2_files: List[FileMetadata] = []
        t1_extensions = {".tf", ".hcl", ".yaml", ".yml", ".json"}
        t1_names = {"docker-compose", "package.json", "requirements.txt", "go.mod", "pom.xml"}
        skip_dirs = {".git", "node_modules", "venv", "__pycache__", "tests", "test"}

        for root, dirs, files in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
                ext = os.path.splitext(file)[1].lower()
                is_t1 = ext in t1_extensions or any(n in file.lower() for n in t1_names)
                if is_t1:
                    tier_1_files.append(FileMetadata(
                        path=rel_path,
                        extension=ext,
                        size_bytes=os.path.getsize(os.path.join(root, file))
                    ))
                elif ext in {".py", ".ts", ".js", ".go", ".java", ".cs", ".rb"}:
                    tier_2_files.append(FileMetadata(
                        path=rel_path,
                        extension=ext,
                        size_bytes=os.path.getsize(os.path.join(root, file))
                    ))
        return ParseableFileSet(tier_1_files=tier_1_files, tier_2_files=tier_2_files)
