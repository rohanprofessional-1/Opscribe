"""
Security service collectors: IAM, KMS, SecretsManager, DirectoryService.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class IAMCollector(BaseCollector):
    """Discover IAM roles."""

    IS_GLOBAL = True

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "IAM")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        iam = self._client("iam")
        paginator = iam.get_paginator("list_roles")

        for page in paginator.paginate():
            for role in page.get("Roles", []):
                rname = role["RoleName"]
                arn = role["Arn"]

                nodes.append(TopologyNode(
                    uid=self._make_uid("iam", f"role/{rname}"),
                    provider="aws",
                    service="IAM",
                    resource_type="security/role",
                    category="security",
                    name=rname,
                    region="global",
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": rname,
                        "name_tag": rname,
                    },
                    properties={
                        "role_name": rname,
                        "created_date": role.get("CreateDate").isoformat() if role.get("CreateDate") else None,
                        "path": role.get("Path"),
                        "max_session_duration": role.get("MaxSessionDuration"),
                    },
                    raw=role,
                ))
        return nodes


class KMSCollector(BaseCollector):
    """Discover customer-managed KMS keys."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "KMS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        kms = self._client("kms")
        paginator = kms.get_paginator("list_keys")

        for page in paginator.paginate():
            for key in page.get("Keys", []):
                kid = key["KeyId"]
                meta = kms.describe_key(KeyId=kid).get("KeyMetadata", {})

                # Only include customer-managed keys
                if meta.get("KeyManager") != "CUSTOMER":
                    continue

                arn = meta.get("Arn", "")
                desc = meta.get("Description") or kid

                nodes.append(TopologyNode(
                    uid=self._make_uid("kms", kid),
                    provider="aws",
                    service="KMS",
                    resource_type="security/encryption_key",
                    category="security",
                    name=desc,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": kid,
                    },
                    properties={
                        "key_id": kid,
                        "key_state": meta.get("KeyState"),
                        "description": meta.get("Description"),
                        "key_usage": meta.get("KeyUsage"),
                        "key_spec": meta.get("KeySpec"),
                    },
                    raw=meta,
                ))
        return nodes


class SecretsManagerCollector(BaseCollector):
    """Discover Secrets Manager secrets."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "SecretsManager")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        sm = self._client("secretsmanager")
        paginator = sm.get_paginator("list_secrets")

        for page in paginator.paginate():
            for secret in page.get("SecretList", []):
                sname = secret["Name"]
                arn = secret.get("ARN", "")

                nodes.append(TopologyNode(
                    uid=self._make_uid("secretsmanager", sname),
                    provider="aws",
                    service="SecretsManager",
                    resource_type="security/secret",
                    category="security",
                    name=sname,
                    region=self.region,
                    account_id=self.account_id,
                    tags=self._get_tags_dict(secret.get("Tags", [])),
                    merge_hints={
                        "arn": arn,
                        "resource_id": sname,
                        "name_tag": sname,
                    },
                    properties={
                        "secret_name": sname,
                        "created_date": secret.get("CreatedDate").isoformat() if secret.get("CreatedDate") else None,
                        "last_accessed_date": secret.get("LastAccessedDate").isoformat() if secret.get("LastAccessedDate") else None,
                        "kms_key_id": secret.get("KmsKeyId"),
                    },
                    raw=secret,
                ))
        return nodes


class DirectoryServiceCollector(BaseCollector):
    """Discover AWS Directory Service directories."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "DirectoryService")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ds = self._client("ds")
        response = ds.describe_directories()

        for directory in response.get("DirectoryDescriptions", []):
            did = directory["DirectoryId"]
            dname = directory.get("Name", did)
            arn = f"arn:aws:ds:{self.region}:{self.account_id}:directory/{did}"

            nodes.append(TopologyNode(
                uid=self._make_uid("ds", did),
                provider="aws",
                service="DirectoryService",
                resource_type="security/directory",
                category="security",
                name=dname,
                region=self.region,
                account_id=self.account_id,
                tags={},
                merge_hints={
                    "arn": arn,
                    "resource_id": did,
                    "name_tag": dname,
                    "dns_name": directory.get("DnsIpAddrs", [None])[0] if directory.get("DnsIpAddrs") else None,
                },
                properties={
                    "directory_id": did,
                    "directory_type": directory.get("Type"),
                    "status": directory.get("Stage"),
                    "vpc_id": directory.get("VpcSettings", {}).get("VpcId"),
                },
                raw=directory,
            ))
        return nodes
