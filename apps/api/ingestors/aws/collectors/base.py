"""
Base collector ABC shared by all service-specific collectors.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.client_factory import AWSClientFactory

logger = logging.getLogger(__name__)

# Services that are global (not region-scoped)
_GLOBAL_SERVICES = frozenset({"iam", "cloudfront"})


class BaseCollector(ABC):
    """Abstract base for every AWS service collector."""

    IS_GLOBAL: bool = False  # Override to True for global collectors (IAM, CloudFront, S3)

    def __init__(self, factory: AWSClientFactory, region: str, account_id: str) -> None:
        self._factory = factory
        self.region = region
        self.account_id = account_id

    # -- Subclass contract ---------------------------------------------------

    @abstractmethod
    def collect(self) -> list[TopologyNode]:
        """Return discovered nodes for this service."""
        ...

    # -- Helpers available to all collectors ---------------------------------

    def _client(self, service: str) -> Any:
        """Shorthand for factory.get_client."""
        return self._factory.get_client(service)

    def _safe_collect(self, fn: Any, service_name: str) -> list[TopologyNode]:
        """Run *fn* and return its nodes; log + swallow errors so one
        failing service never kills the whole scan."""
        try:
            return fn()
        except Exception as e:
            logger.warning(f"{service_name} discovery error: {e}")
            return []

    def _make_uid(self, service_prefix: str, resource_id: str) -> str:
        """Build a deterministic uid.

        Global services (IAM, CloudFront) use ``"global"`` as the region
        segment; all others use the scan region.
        """
        region = "global" if service_prefix in _GLOBAL_SERVICES else self.region
        return f"aws::{region}::{service_prefix}::{resource_id}"

    # -- Tag helpers ---------------------------------------------------------

    @staticmethod
    def _get_name_tag(tags: list[dict] | None) -> str | None:
        """Extract the ``Name`` tag from a typical AWS tag list."""
        if not tags:
            return None
        for tag in tags:
            if tag.get("Key") == "Name" or tag.get("key") == "Name":
                return tag.get("Value")
        return None

    @staticmethod
    def _get_tags_dict(tags: list[dict] | None) -> dict[str, str]:
        """Convert an AWS tag list ``[{Key:…, Value:…}]`` to a plain dict."""
        if not tags:
            return {}
        return {
            (tag.get("Key") or tag.get("key")): (tag.get("Value") or tag.get("value"))
            for tag in tags
            if tag.get("Key") or tag.get("key")
        }
