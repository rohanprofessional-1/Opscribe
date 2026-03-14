from dataclasses import dataclass
from typing import List

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
