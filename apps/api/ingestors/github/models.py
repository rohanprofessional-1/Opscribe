from dataclasses import dataclass
from typing import List, Dict, Any
from pydantic import BaseModel, Field


# --- Repo Walker Models ---

@dataclass
class FileMetadata:
    path: str
    extension: str
    size_bytes: int
    last_commit_sha: str

@dataclass
class ParseableFileSet:
    tier_1_files: List[FileMetadata]
    tier_2_files: List[FileMetadata]


# --- Parser Models ---

class InfrastructureSignal(BaseModel):
    component_type: str = Field(description="The architectural archetype, e.g., 'Database', 'Cache', 'Worker', 'Queue', 'API', 'Storage'")
    name: str = Field(description="The logical name of the component, e.g., 'main-db', 'redis-cache'")
    config: Dict[str, Any] = Field(description="Raw extracted configuration, connection strings, or metadata")
    source_location: str = Field(description="The file path where this signal was extracted from")
    confidence_score: float = Field(description="A score between 0.0 and 1.0 indicating extraction confidence")
