from abc import ABC, abstractmethod
from typing import List
from apps.api.ingestors.aws.schemas import DiscoveryResult

class BaseDetector(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """The name of the discovery source (e.g., 'aws', 'github')."""
        pass

    @abstractmethod
    async def discover(self, **kwargs) -> DiscoveryResult:
        """Perform discovery and return normalized nodes and edges."""
        pass
