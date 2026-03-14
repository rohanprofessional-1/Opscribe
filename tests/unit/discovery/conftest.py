"""
Pytest configuration and fixtures for AWS discovery unit tests.

This file provides shared fixtures for all discovery-related tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the apps/api directory to the Python path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "apps" / "api"))
sys.path.insert(0, str(repo_root))

from apps.api.ingestors.aws.detector import AWSDetector
from tests.integration.discovery.mock_aws_cluster import MockAWSCluster


@pytest.fixture
def aws_detector():
    """Create an AWS detector instance for testing"""
    return AWSDetector(region_name="us-east-1")


@pytest.fixture
def mock_cluster():
    """Fixture that provides a MockAWSCluster instance"""
    return MockAWSCluster(service_name="opscribe-test")


@pytest.fixture
def mock_boto_responses(mock_cluster):
    """Fixture that provides all mock AWS API responses from the cluster"""
    return {
        "vpc": mock_cluster.vpc(),
        "subnets": mock_cluster.subnets(),
        "ec2_instances": mock_cluster.describe_instances_response(),
        "rds": mock_cluster.describe_db_instances_response(),
        "s3_buckets": mock_cluster.list_buckets_response(),
        "sqs_queues": mock_cluster.list_queues_response(),
    }


@pytest.fixture
def mocked_aws_detector(mock_cluster):
    """
    Fixture that provides a fully mocked AWSDetector.
    All boto3 calls are intercepted and return mock_cluster data.
    """
    with patch("boto3.client") as mock_boto_client:
        detector = AWSDetector(region_name="us-east-1")
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        mock_client.get_caller_identity.return_value = {
            "Account": mock_cluster.account_id
        }

        def boto_client_side_effect(service, **kwargs):
            """Route to the correct mock service"""
            if service == "ec2":
                ec2_client = MagicMock()
                ec2_client.describe_instances.return_value = mock_cluster.describe_instances_response()
                ec2_client.describe_volumes.return_value = {"Volumes": []}
                ec2_client.describe_vpcs.return_value = {"Vpcs": [mock_cluster.vpc()]}
                ec2_client.describe_load_balancers.return_value = {"LoadBalancers": []}
                return ec2_client
            elif service == "rds":
                rds_client = MagicMock()
                rds_client.describe_db_instances.return_value = mock_cluster.describe_db_instances_response()
                rds_client.describe_db_clusters.return_value = {"DBClusters": []}
                return rds_client
            elif service == "s3":
                s3_client = MagicMock()
                s3_client.list_buckets.return_value = mock_cluster.list_buckets_response()
                s3_client.get_bucket_tagging.return_value = mock_cluster.get_bucket_tagging_response()
                return s3_client
            elif service == "sqs":
                sqs_client = MagicMock()
                sqs_client.list_queues.return_value = mock_cluster.list_queues_response()
                return sqs_client
            elif service == "lambda":
                lambda_client = MagicMock()
                paginator = MagicMock()
                paginator.paginate.return_value = [{"Functions": []}]
                lambda_client.get_paginator.return_value = paginator
                return lambda_client
            elif service == "ecs":
                ecs_client = MagicMock()
                ecs_client.list_clusters.return_value = {"clusterArns": []}
                return ecs_client
            elif service == "eks":
                eks_client = MagicMock()
                eks_client.list_clusters.return_value = {"clusters": []}
                return eks_client
            elif service == "efs":
                efs_client = MagicMock()
                efs_client.describe_file_systems.return_value = {"FileSystems": []}
                return efs_client
            elif service == "fsx":
                fsx_client = MagicMock()
                fsx_client.describe_file_systems.return_value = {"FileSystems": []}
                return fsx_client
            elif service == "dynamodb":
                dynamo_client = MagicMock()
                dynamo_client.list_tables.return_value = {"TableNames": []}
                return dynamo_client
            elif service == "redshift":
                redshift_client = MagicMock()
                redshift_client.describe_clusters.return_value = {"Clusters": []}
                return redshift_client
            elif service == "elbv2":
                elbv2_client = MagicMock()
                elbv2_client.describe_load_balancers.return_value = {"LoadBalancers": []}
                return elbv2_client
            elif service == "cloudfront":
                cf_client = MagicMock()
                cf_client.list_distributions.return_value = {"DistributionList": {"Items": []}}
                return cf_client
            elif service == "directconnect":
                dx_client = MagicMock()
                dx_client.describe_connections.return_value = {"connections": []}
                return dx_client
            elif service == "iam":
                iam_client = MagicMock()
                iam_client.list_roles.return_value = {"Roles": []}
                return iam_client
            elif service == "kms":
                kms_client = MagicMock()
                kms_client.list_keys.return_value = {"Keys": []}
                return kms_client
            elif service == "secretsmanager":
                secrets_client = MagicMock()
                secrets_client.list_secrets.return_value = {"SecretList": []}
                return secrets_client
            elif service == "ds":
                ds_client = MagicMock()
                ds_client.describe_directories.return_value = {"DirectoryDescriptions": []}
                return ds_client
            elif service == "logs":
                logs_client = MagicMock()
                logs_client.describe_log_groups.return_value = {"logGroups": []}
                return logs_client
            elif service == "cloudtrail":
                ct_client = MagicMock()
                ct_client.describe_trails.return_value = {"trailList": []}
                return ct_client
            elif service == "ssm":
                ssm_client = MagicMock()
                ssm_client.describe_parameters.return_value = {"Parameters": []}
                return ssm_client
            elif service == "sns":
                sns_client = MagicMock()
                sns_client.list_topics.return_value = {"Topics": []}
                return sns_client
            elif service == "events":
                events_client = MagicMock()
                events_client.list_rules.return_value = {"Rules": []}
                return events_client
            elif service == "apigateway":
                apigw_client = MagicMock()
                apigw_client.get_rest_apis.return_value = {"items": []}
                return apigw_client
            elif service == "sts":
                sts_client = MagicMock()
                sts_client.get_caller_identity.return_value = {
                    "Account": mock_cluster.account_id
                }
                return sts_client
            else:
                return MagicMock()

        mock_boto_client.side_effect = boto_client_side_effect
        yield detector, mock_cluster


@pytest.fixture
def mock_cluster_with_detailed_setup(mock_cluster):
    """
    Enhanced fixture with more detailed infrastructure setup.
    Useful for testing complex scenarios.
    """
    return {
        "cluster": mock_cluster,
        "expected_resource_count": 6,
        "expected_vpc_count": 1,
        "expected_subnet_count": 2,
        "expected_ec2_count": 2,
        "expected_rds_count": 1,
        "expected_s3_count": 1,
        "expected_sqs_count": 1,
    }
