import os
import shutil
import subprocess
import logging
from uuid import UUID
from datetime import datetime
from sqlmodel import Session
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from apps.api.infrastructure.rag.models import KnowledgeBaseItem
from apps.api.infrastructure.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class RepoIngestor:
    def __init__(self, session: Session):
        self.session = session
        self.embedding_service = EmbeddingService()
        self.base_tmp_dir = "/tmp/opscribe"
        
        # Define files that we care about based on extension
        self.allowed_extensions = {
            ".py", ".js", ".ts", ".go", ".java", ".md", ".json", 
            ".yaml", ".yml", ".toml", ".ini", ".env.example", ".sh",
            ".tf", ".hcl"
        }
        
        # Some special files to include regardless of extension
        self.included_files = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile"}
        
        # Directories to ignore
        self.ignored_dirs = {".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__"}

    def ingest_repo(self, repo_url: str, tenant_id: UUID, ref: str = "main") -> int:
        """
        Clones a repository, processes its files into chunks, and saves to the database.
        Returns the number of chunks ingested.
        """
        # Create a unique temporary path for this clone
        repo_name = repo_url.rstrip('/').split('/')[-1].replace(".git", "")
        tmp_dir = os.path.join(self.base_tmp_dir, str(tenant_id), repo_name)
        
        chunks_created = 0
        try:
            # 1. Clone repository
            self._clone_repo(repo_url, tmp_dir, ref)
            
            # 2. Extract and process files
            for root, dirs, files in os.walk(tmp_dir):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
                
                for file in files:
                    if self._is_relevant_file(file):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, tmp_dir)
                        
                        try:
                            # 3. Read -> Chunk -> Embed -> Insert
                            file_chunks = self._process_file(file_path, relative_path, tenant_id)
                            chunks_created += len(file_chunks)
                        except Exception as e:
                            logger.error(f"Failed to process file {relative_path}: {e}")
                            
            # Commit all chunks to the database
            self.session.commit()
            return chunks_created
            
        finally:
            # 4. Cleanup
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)

    def _clone_repo(self, repo_url: str, dest_dir: str, ref: str):
        """Clones a repository using system git."""
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
            
        os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
        
        try:
            # Note: We do a shallow clone to save time
            cmd = ["git", "clone", "--depth", "1", "--branch", ref, repo_url, dest_dir]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise HTTPException(status_code=400, detail=f"Failed to clone repository. Is the URL public and correct? Error: {e.stderr}")
            
    def _is_relevant_file(self, filename: str) -> bool:
        """Determines if a file should be parsed."""
        if filename in self.included_files:
            return True
        _, ext = os.path.splitext(filename)
        return ext in self.allowed_extensions

    def _process_file(self, file_path: str, relative_path: str, tenant_id: UUID) -> List[KnowledgeBaseItem]:
        """Reads a file, chunks it, embeds it, and saves it to DB session."""
        
        # Read file content safely
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary or non-utf8 files
            return []
            
        # Basic Chunker Settings (Character-based for simplicity)
        max_chunk_size = 3000   # chars roughly ~700-800 tokens
        overlap = 300           # char overlap
        
        chunks = self._chunk_text(content, max_chunk_size, overlap)
        items = []
        
        # Use existing graph_id structure (we can invent a consistent dummy one or use tenant_id for simplicity)
        # Note: In GraphIngestor, graph_id binds to ArchitectureGraph. We'll use a nil UUID or tenant_id if not linked to a specific graph yet.
        # Alternatively, the schema uses graph_id as a required field but index=True.
        # We'll use a deterministic dummy UUID for "Repo Root" or just use tenant_id for now.
        dummy_graph_id = tenant_id 
        dummy_entity_id = tenant_id

        for i, chunk_text in enumerate(chunks):
            # Prepend Context to Chunk
            contextual_chunk = f"File: {relative_path}\n\n{chunk_text}"
            
            # Embed
            embedding = self.embedding_service.generate_embedding(contextual_chunk)
            
            item = KnowledgeBaseItem(
                tenant_id=tenant_id,
                graph_id=dummy_graph_id,    # Might need adjusting based on graph creation intent later
                entity_id=dummy_entity_id,  # Will bypass FK constraints if not enforced directly
                content=contextual_chunk,
                embedding=embedding,
                metadata_={
                    "type": "repo_chunk",
                    "file_path": relative_path,
                    "chunk_index": i
                },
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            self.session.add(item)
            items.append(item)
            
        return items

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Splits text into chunks of `chunk_size` characters with `overlap` characters of overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks
