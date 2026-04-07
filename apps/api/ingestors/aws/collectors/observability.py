"""
Observability service collectors: CloudWatch, CloudTrail, SSM.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class CloudWatchCollector(BaseCollector):
    """Discover CloudWatch log groups."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "CloudWatch")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        logs = self._client("logs")
        paginator = logs.get_paginator("describe_log_groups")

        for page in paginator.paginate():
            for lg in page.get("logGroups", []):
                lgname = lg["logGroupName"]
                arn = lg.get("arn", f"arn:aws:logs:{self.region}:{self.account_id}:log-group:{lgname}")

                nodes.append(TopologyNode(
                    uid=self._make_uid("logs", lgname),
                    provider="aws",
                    service="CloudWatch",
                    resource_type="observability/log_group",
                    category="observability",
                    name=lgname,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": lgname,
                        "name_tag": lgname,
                    },
                    properties={
                        "log_group_name": lgname,
                        "retention_in_days": lg.get("retentionInDays"),
                        "stored_bytes": lg.get("storedBytes"),
                    },
                    raw=lg,
                ))
        return nodes


class CloudTrailCollector(BaseCollector):
    """Discover CloudTrail trails."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "CloudTrail")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ct = self._client("cloudtrail")
        response = ct.describe_trails()

        for trail in response.get("trailList", []):
            tname = trail.get("Name", trail.get("TrailARN", "").split(":trail/")[-1])
            arn = trail.get("TrailARN", "")

            nodes.append(TopologyNode(
                uid=self._make_uid("cloudtrail", tname),
                provider="aws",
                service="CloudTrail",
                resource_type="observability/audit_trail",
                category="observability",
                name=tname,
                region=self.region,
                account_id=self.account_id,
                tags={},
                merge_hints={
                    "arn": arn,
                    "resource_id": tname,
                    "name_tag": tname,
                },
                properties={
                    "trail_name": tname,
                    "s3_bucket_name": trail.get("S3BucketName"),
                    "is_multi_region_trail": trail.get("IsMultiRegionTrail"),
                    "home_region": trail.get("HomeRegion"),
                    "log_file_validation_enabled": trail.get("LogFileValidationEnabled"),
                },
                raw=trail,
            ))
        return nodes


class SSMCollector(BaseCollector):
    """Discover SSM parameters."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "SSM")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ssm = self._client("ssm")
        paginator = ssm.get_paginator("describe_parameters")

        for page in paginator.paginate():
            for param in page.get("Parameters", []):
                pname = param["Name"]
                arn = f"arn:aws:ssm:{self.region}:{self.account_id}:parameter{pname}"

                nodes.append(TopologyNode(
                    uid=self._make_uid("ssm", f"parameter{pname}"),
                    provider="aws",
                    service="SSM",
                    resource_type="observability/parameter",
                    category="observability",
                    name=pname,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": pname,
                        "name_tag": pname,
                    },
                    properties={
                        "parameter_name": pname,
                        "type": param.get("Type"),
                        "version": param.get("Version"),
                        "last_modified_date": param.get("LastModifiedDate").isoformat() if param.get("LastModifiedDate") else None,
                    },
                    raw=param,
                ))
        return nodes
