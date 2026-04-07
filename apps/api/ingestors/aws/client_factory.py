"""
AWS credential resolution and boto3 client creation.

Extracted from the original AWSDetector._get_client method.
Instantiated once in detector.py and injected into all collectors.
"""

from __future__ import annotations

import os
import logging
from typing import Any

import boto3
from dotenv import dotenv_values

logger = logging.getLogger(__name__)


class AWSClientFactory:
    """Creates boto3 service clients using tenant credentials or STS AssumeRole."""

    def __init__(self, region_name: str, credentials: dict[str, Any]) -> None:
        self.region_name = region_name
        self.credentials = credentials or {}
        self._temp_credentials: dict | None = None

    # -- Public API ----------------------------------------------------------

    def get_client(self, service_name: str) -> Any:
        """Return a configured boto3 client for *service_name*."""
        access_key, secret_key, session_token = self._resolve_credentials()

        # The factory is already initialized with the specific region we want.
        # Fallback to us-east-1 only if self.region_name is somehow missing.
        region = self.region_name or "us-east-1"

        client_kwargs: dict[str, Any] = {
            "service_name": service_name,
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }

        if session_token:
            client_kwargs["aws_session_token"] = session_token

        # S3 local-endpoint support (e.g. MinIO)
        endpoint_url = self.credentials.get("endpoint_url")
        if service_name == "s3" and endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        return boto3.client(**client_kwargs)

    # -- Internals -----------------------------------------------------------

    def _resolve_credentials(self) -> tuple[str | None, str | None, str | None]:
        """Return (access_key, secret_key, session_token) after optional STS assume-role."""
        role_arn = self.credentials.get("role_arn")

        if role_arn:
            if not self._temp_credentials:
                self._temp_credentials = self._assume_role(role_arn)

            return (
                self._temp_credentials["AccessKeyId"],
                self._temp_credentials["SecretAccessKey"],
                self._temp_credentials["SessionToken"],
            )

        return (
            self.credentials.get("aws_access_key_id"),
            self.credentials.get("aws_secret_access_key"),
            self.credentials.get("aws_session_token"),
        )

    def _assume_role(self, role_arn: str) -> dict:
        """STS AssumeRole using Opscribe's broker credentials. Result is cached."""
        env = dotenv_values("apps/api/.env")

        sts_access = env.get("OPSCRIBE_AWS_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID")
        sts_secret = env.get("OPSCRIBE_AWS_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")

        sts_kwargs: dict[str, Any] = {
            "service_name": "sts",
            "region_name": self.region_name,
        }
        if sts_access:
            sts_kwargs["aws_access_key_id"] = sts_access
            sts_kwargs["aws_secret_access_key"] = sts_secret

        sts = boto3.client(**sts_kwargs)

        assume_kwargs: dict[str, Any] = {
            "RoleArn": role_arn,
            "RoleSessionName": "OpscribeDiscovery",
        }
        external_id = self.credentials.get("external_id")
        if external_id:
            assume_kwargs["ExternalId"] = external_id

        logger.info(f"Assuming role {role_arn} for discovery...")
        response = sts.assume_role(**assume_kwargs)
        return response["Credentials"]
