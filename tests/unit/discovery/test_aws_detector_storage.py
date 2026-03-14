"""
Unit tests for AWS Storage Services: S3, EBS, EFS, FSx

These tests verify that the detector correctly identifies storage resources
with proper attributes and properties.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from apps.api.ingestors.aws.detector import AWSDetector


class TestS3Discovery:
    """Test S3 bucket discovery"""

    @patch("boto3.client")
    def test_discover_s3_buckets(self, mock_boto_client, aws_detector):
        """Test S3 bucket discovery"""
        s3_mock = MagicMock()
        mock_boto_client.return_value = s3_mock

        s3_mock.list_buckets.return_value = {
            "Buckets": [
                {"Name": "my-app-data", "CreationDate": datetime(2024, 1, 15)},
                {"Name": "my-app-logs", "CreationDate": datetime(2024, 1, 20)},
            ]
        }
        s3_mock.get_bucket_tagging.return_value = {
            "TagSet": [{"Key": "Environment", "Value": "prod"}]
        }

        nodes = aws_detector._discover_s3()

        assert len(nodes) == 2
        assert nodes[0].key == "s3:my-app-data"
        assert nodes[0].properties["service"] == "S3"
        assert nodes[1].key == "s3:my-app-logs"

    @patch("boto3.client")
    def test_discover_ebs_volumes(self, mock_boto_client, aws_detector):
        """Test EBS volume discovery"""
        ec2_mock = MagicMock()
        mock_boto_client.return_value = ec2_mock

        ec2_mock.describe_volumes.return_value = {
            "Volumes": [
                {
                    "VolumeId": "vol-12345678",
                    "Size": 100,
                    "VolumeType": "gp3",
                    "State": "in-use",
                    "AvailabilityZone": "us-east-1a",
                    "Attachments": [{"InstanceId": "i-1234567890abcdef0"}],
                    "Tags": [{"Key": "Name", "Value": "data-volume"}],
                }
            ]
        }

        nodes = aws_detector._discover_ebs()

        assert len(nodes) == 1
        assert nodes[0].key == "ebs:vol-12345678"
        assert nodes[0].properties["service"] == "EBS"
        assert nodes[0].properties["size"] == 100
        assert nodes[0].properties["volume_type"] == "gp3"

    @patch("boto3.client")
    def test_discover_efs_file_systems(self, mock_boto_client, aws_detector):
        """Test EFS file system discovery"""
        efs_mock = MagicMock()
        mock_boto_client.return_value = efs_mock

        efs_mock.describe_file_systems.return_value = {
            "FileSystems": [
                {
                    "FileSystemId": "fs-12345678",
                    "Name": "shared-storage",
                    "LifeCycleState": "available",
                    "SizeInBytes": {"Value": 1099511627776},
                    "PerformanceMode": "generalPurpose",
                    "ThroughputMode": "bursting",
                    "FileSystemArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
                }
            ]
        }

        nodes = aws_detector._discover_efs()

        assert len(nodes) == 1
        assert nodes[0].key == "efs:fs-12345678"
        assert nodes[0].properties["service"] == "EFS"

    @patch("boto3.client")
    def test_discover_fsx_file_systems(self, mock_boto_client, aws_detector):
        """Test FSx file system discovery"""
        fsx_mock = MagicMock()
        mock_boto_client.return_value = fsx_mock

        fsx_mock.describe_file_systems.return_value = {
            "FileSystems": [
                {
                    "FileSystemId": "fs-0123456789abcdef0",
                    "FileSystemType": "WINDOWS",
                    "Lifecycle": "AVAILABLE",
                    "StorageCapacity": 2048,
                    "VpcId": "vpc-12345678",
                    "ResourceARN": "arn:aws:fsx:us-east-1:123456789012:file-system/fs-0123456789abcdef0",
                }
            ]
        }

        nodes = aws_detector._discover_fsx()

        assert len(nodes) == 1
        assert nodes[0].key == "fsx:fs-0123456789abcdef0"
        assert nodes[0].properties["service"] == "FSx"
