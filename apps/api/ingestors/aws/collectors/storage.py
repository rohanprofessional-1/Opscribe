"""
Storage service collectors: S3, EBS, EFS, FSx.
"""

from __future__ import annotations

from botocore.exceptions import ClientError

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class S3Collector(BaseCollector):
    """Discover S3 buckets.

    S3 is global — list_buckets returns all buckets regardless of region.
    Each bucket's uid and region field reflect its actual location.
    """

    IS_GLOBAL = True

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "S3")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        s3 = self._client("s3")
        response = s3.list_buckets()

        for bucket in response.get("Buckets", []):
            bname = bucket["Name"]

            # Tags
            try:
                tags_dict = self._get_tags_dict(
                    s3.get_bucket_tagging(Bucket=bname).get("TagSet", [])
                )
            except ClientError:
                tags_dict = {}

            # Location — determines the bucket's actual region
            try:
                location = s3.get_bucket_location(Bucket=bname).get("LocationConstraint") or "us-east-1"
            except ClientError:
                location = self.region

            # Notification Configurations
            try:
                notif = s3.get_bucket_notification_configuration(Bucket=bname)
                lambda_triggers = [
                    conf.get("LambdaFunctionArn")
                    for conf in notif.get("LambdaFunctionConfigurations", [])
                    if conf.get("LambdaFunctionArn")
                ]
            except ClientError as e:
                self.logger.warning(f"Failed to get notifications for bucket {bname}: {e}")
                lambda_triggers = []

            arn = f"arn:aws:s3:::{bname}"
            # S3 uid uses the actual bucket region, not the bootstrap region
            bucket_uid = f"aws::{location}::s3::{bname}"

            nodes.append(TopologyNode(
                uid=bucket_uid,
                provider="aws",
                service="S3",
                resource_type="storage/bucket",
                category="storage",
                name=bname,
                region=location,
                account_id=self.account_id,
                tags=tags_dict,
                merge_hints={
                    "arn": arn,
                    "resource_id": bname,
                    "name_tag": bname,
                },
                properties={
                    "bucket_name": bname,
                    "creation_date": bucket.get("CreationDate").isoformat() if bucket.get("CreationDate") else None,
                    "location": location,
                    "lambda_triggers": lambda_triggers,
                },
                raw=bucket,
            ))
        return nodes


class EBSCollector(BaseCollector):
    """Discover EBS volumes."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "EBS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ec2 = self._client("ec2")
        paginator = ec2.get_paginator("describe_volumes")

        for page in paginator.paginate():
            for vol in page.get("Volumes", []):
                vid = vol["VolumeId"]
                name = self._get_name_tag(vol.get("Tags", []))
                arn = f"arn:aws:ec2:{self.region}:{self.account_id}:volume/{vid}"

                nodes.append(TopologyNode(
                    uid=self._make_uid("ebs", vid),
                    provider="aws",
                    service="EBS",
                    resource_type="storage/block_volume",
                    category="storage",
                    name=name or vid,
                    region=self.region,
                    account_id=self.account_id,
                    tags=self._get_tags_dict(vol.get("Tags", [])),
                    merge_hints={
                        "arn": arn,
                        "resource_id": vid,
                        "name_tag": name,
                    },
                    properties={
                        "volume_id": vid,
                        "size": vol["Size"],
                        "volume_type": vol["VolumeType"],
                        "state": vol["State"],
                        "availability_zone": vol["AvailabilityZone"],
                        "attached_to": [att["InstanceId"] for att in vol.get("Attachments", [])],
                        "encrypted": vol.get("Encrypted"),
                        "iops": vol.get("Iops"),
                    },
                    raw=vol,
                ))
        return nodes


class EFSCollector(BaseCollector):
    """Discover EFS file systems."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "EFS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        efs = self._client("efs")
        response = efs.describe_file_systems()

        for fs in response.get("FileSystems", []):
            fsid = fs["FileSystemId"]
            name = fs.get("Name", fsid)
            arn = fs.get("FileSystemArn", "")

            nodes.append(TopologyNode(
                uid=self._make_uid("efs", fsid),
                provider="aws",
                service="EFS",
                resource_type="storage/file_system",
                category="storage",
                name=name,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(fs.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": fsid,
                    "name_tag": name,
                },
                properties={
                    "file_system_id": fsid,
                    "state": fs["LifeCycleState"],
                    "size_bytes": fs.get("SizeInBytes", {}).get("Value"),
                    "performance_mode": fs.get("PerformanceMode"),
                    "throughput_mode": fs.get("ThroughputMode"),
                },
                raw=fs,
            ))
        return nodes


class FSxCollector(BaseCollector):
    """Discover FSx file systems."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "FSx")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        fsx = self._client("fsx")
        response = fsx.describe_file_systems()

        for fs in response.get("FileSystems", []):
            fsid = fs["FileSystemId"]
            arn = fs.get("ResourceARN", "")

            nodes.append(TopologyNode(
                uid=self._make_uid("fsx", fsid),
                provider="aws",
                service="FSx",
                resource_type="storage/file_system",
                category="storage",
                name=fsid,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(fs.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": fsid,
                },
                properties={
                    "file_system_id": fsid,
                    "file_system_type": fs["FileSystemType"],
                    "lifecycle": fs["Lifecycle"],
                    "storage_capacity": fs.get("StorageCapacity"),
                    "vpc_id": fs.get("VpcId"),
                },
                raw=fs,
            ))
        return nodes
