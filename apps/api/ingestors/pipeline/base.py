"""
Base classes for the ingestion pipeline architecture.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from apps.api.ingestors.aws.schemas import DiscoveryResult

class BaseIngestor(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source (e.g., 'aws', 'github')"""
        ...

    @abstractmethod
    async def ingest(self) -> List[DiscoveryResult]:
        """Run the ingestion process and return discovery results"""
        ...


class BaseExporter(ABC):
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Name of the export backend (e.g., 's3', 'local')"""
        ...

    @abstractmethod
    async def export(
        self,
        client_id: str,
        results: List[DiscoveryResult],
        label: Optional[str] = None,
    ) -> str:
        """
        Export the combined discovery results to the backend.
        
        Args:
            client_id: The tenant/client ID string
            results: List of DiscoveryResult objects
            label: Optional descriptive label (used for naming exported files)
            
        Returns:
            str: Identifier/path of the exported data
        """
        ...

    @abstractmethod
    async def load_current(self, client_id: str) -> List[DiscoveryResult]:
        """
        Load the combined 'current' state of all sources for a client from the backend.
        
        Args:
            client_id: The tenant/client ID string
            
        Returns:
            List[DiscoveryResult]: Combined list of results from all sources
        """
        ...
