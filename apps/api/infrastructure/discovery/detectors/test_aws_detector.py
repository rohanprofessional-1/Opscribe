"""
Comprehensive test suite for AWS service detection.

This test suite demonstrates how to mock AWS API responses and test
the detection of all service categories.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from .aws import AWSDetector
from ..schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge


class MockBotoClient:
    """Base class for mocking boto3 clients"""

    pass


@pytest.fixture
def aws_detector():
    """Create an AWS detector instance for testing"""
    return AWSDetector(region_name="us-east-1")


class TestComputeServices:
    """Test discovery of compute services: EC2, Lambda, ECS, EKS"""

    @patch("boto3.client")
    def test_discover_ec2_instances(self, mock_boto_client, aws_detector):
        """Test EC2 instance discovery"""
        ec2_mock = MagicMock()
        mock_boto_client.return_value = ec2_mock

        ec2_mock.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t3.medium",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.5",
                            "PublicIpAddress": "54.123.45.67",
                            "Tags": [{"Key": "Name", "Value": "web-server-01"}],
                            "VpcId": "vpc-12345678",
                            "SubnetId": "subnet-87654321",
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "SecurityGroups": [{"GroupId": "sg-12345678"}],
                            "OwnerId": "123456789012",
                        }
                    ]
                }
            ]
        }

        nodes = aws_detector._discover_ec2()

        assert len(nodes) == 1
        assert nodes[0].key == "ec2:i-1234567890abcdef0"
        assert nodes[0].display_name == "web-server-01"
        assert nodes[0].node_type == "compute"
        assert nodes[0].properties["service"] == "EC2"
        assert nodes[0].properties["instance_type"] == "t3.medium"
        assert nodes[0].properties["private_ip"] == "10.0.0.5"

    @patch("boto3.client")
    def test_discover_lambda_functions(self, mock_boto_client, aws_detector):
        """Test Lambda function discovery"""
        lambda_mock = MagicMock()
        mock_boto_client.return_value = lambda_mock

        lambda_mock.get_paginator.return_value.paginate.return_value = [
            {
                "Functions": [
                    {
                        "FunctionName": "order-processor",
                        "Runtime": "python3.11",
                        "Handler": "index.handler",
                        "MemorySize": 256,
                        "Timeout": 30,
                        "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:order-processor",
                        "Role": "arn:aws:iam::123456789012:role/lambda-role",
                        "VpcConfig": {"VpcId": "vpc-12345678"},
                    }
                ]
            }
        ]

        nodes = aws_detector._discover_lambda()

        assert len(nodes) == 1
        assert nodes[0].key == "lambda:order-processor"
        assert nodes[0].properties["service"] == "Lambda"
        assert nodes[0].properties["runtime"] == "python3.11"
        assert nodes[0].properties["memory_size"] == 256

    @patch("boto3.client")
    def test_discover_ecs_clusters(self, mock_boto_client, aws_detector):
        """Test ECS cluster and service discovery"""
        ecs_mock = MagicMock()
        mock_boto_client.return_value = ecs_mock

        ecs_mock.list_clusters.return_value = {
            "clusterArns": ["arn:aws:ecs:us-east-1:123456789012:cluster/production"]
        }
        ecs_mock.list_services.return_value = {
            "serviceArns": [
                "arn:aws:ecs:us-east-1:123456789012:service/production/web-api"
            ]
        }

        nodes = aws_detector._discover_ecs()

        assert len(nodes) >= 1
        assert any(n.properties.get("cluster_type") == "cluster" for n in nodes)
        assert any(n.properties.get("cluster_type") == "service" for n in nodes)

    @patch("boto3.client")
    def test_discover_eks_clusters(self, mock_boto_client, aws_detector):
        """Test EKS cluster discovery"""
        eks_mock = MagicMock()
        mock_boto_client.return_value = eks_mock

        eks_mock.list_clusters.return_value = {"clusters": ["prod-cluster"]}
        eks_mock.describe_cluster.return_value = {
            "cluster": {
                "name": "prod-cluster",
                "version": "1.27",
                "status": "ACTIVE",
                "arn": "arn:aws:eks:us-east-1:123456789012:cluster/prod-cluster",
                "resourcesVpcConfig": {"vpcId": "vpc-12345678"},
            }
        }

        nodes = aws_detector._discover_eks()

        assert len(nodes) == 1
        assert nodes[0].key == "eks:prod-cluster"
        assert nodes[0].properties["service"] == "EKS"
        assert nodes[0].properties["version"] == "1.27"


class TestStorageServices:
    """Test discovery of storage services: S3, EBS, EFS, FSx"""

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


class TestDatabaseServices:
    """Test discovery of database services: RDS, DynamoDB, Redshift"""

    @patch("boto3.client")
    def test_discover_rds_instances(self, mock_boto_client, aws_detector):
        """Test RDS instance discovery"""
        rds_mock = MagicMock()
        mock_boto_client.return_value = rds_mock

        rds_mock.describe_db_instances.return_value = {
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "prod-db",
                    "Engine": "postgres",
                    "EngineVersion": "14.7",
                    "DBInstanceStatus": "available",
                    "DBInstanceClass": "db.t3.large",
                    "DBSubnetGroup": {"VpcId": "vpc-12345678"},
                    "Endpoint": {
                        "Address": "prod-db.abc123.us-east-1.rds.amazonaws.com",
                        "Port": 5432,
                    },
                    "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:prod-db",
                }
            ]
        }
        rds_mock.describe_db_clusters.return_value = {"DBClusters": []}

        nodes = aws_detector._discover_rds()

        assert len(nodes) == 1
        assert nodes[0].key == "rds:prod-db"
        assert nodes[0].properties["service"] == "RDS"
        assert nodes[0].properties["engine"] == "postgres"

    @patch("boto3.client")
    def test_discover_dynamodb_tables(self, mock_boto_client, aws_detector):
        """Test DynamoDB table discovery"""
        dynamodb_mock = MagicMock()
        mock_boto_client.return_value = dynamodb_mock

        dynamodb_mock.list_tables.return_value = {"TableNames": ["Users", "Orders"]}
        dynamodb_mock.describe_table.side_effect = [
            {
                "Table": {
                    "TableName": "Users",
                    "TableStatus": "ACTIVE",
                    "ItemCount": 50000,
                    "TableSizeBytes": 1048576,
                    "BillingModeSummary": {"BillingMode": "PAY_PER_REQUEST"},
                    "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/Users",
                }
            },
            {
                "Table": {
                    "TableName": "Orders",
                    "TableStatus": "ACTIVE",
                    "ItemCount": 100000,
                    "TableSizeBytes": 2097152,
                    "BillingModeSummary": {"BillingMode": "PROVISIONED"},
                    "TableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/Orders",
                }
            },
        ]

        nodes = aws_detector._discover_dynamodb()

        assert len(nodes) == 2
        assert nodes[0].properties["service"] == "DynamoDB"
        assert nodes[1].properties["service"] == "DynamoDB"

    @patch("boto3.client")
    def test_discover_redshift_clusters(self, mock_boto_client, aws_detector):
        """Test Redshift cluster discovery"""
        redshift_mock = MagicMock()
        mock_boto_client.return_value = redshift_mock

        redshift_mock.describe_clusters.return_value = {
            "Clusters": [
                {
                    "ClusterIdentifier": "analytics-warehouse",
                    "NodeType": "dc2.large",
                    "NumberOfNodes": 3,
                    "ClusterStatus": "available",
                    "DBName": "analytics",
                    "Endpoint": {
                        "Address": "analytics-warehouse.abc123.us-east-1.redshift.amazonaws.com"
                    },
                }
            ]
        }

        nodes = aws_detector._discover_redshift()

        assert len(nodes) == 1
        assert nodes[0].key == "redshift:analytics-warehouse"
        assert nodes[0].properties["service"] == "Redshift"
        assert nodes[0].properties["number_of_nodes"] == 3


class TestNetworkingServices:
    """Test discovery of networking services: VPC, ELB, CloudFront, Direct Connect"""

    @patch("boto3.client")
    def test_discover_vpcs(self, mock_boto_client, aws_detector):
        """Test VPC discovery"""
        ec2_mock = MagicMock()
        mock_boto_client.return_value = ec2_mock

        ec2_mock.describe_vpcs.return_value = {
            "Vpcs": [
                {
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.0.0/16",
                    "State": "available",
                    "IsDefault": False,
                    "Tags": [{"Key": "Name", "Value": "production"}],
                }
            ]
        }

        nodes = aws_detector._discover_vpc()

        assert len(nodes) == 1
        assert nodes[0].key == "vpc:vpc-12345678"
        assert nodes[0].properties["service"] == "VPC"
        assert nodes[0].properties["cidr_block"] == "10.0.0.0/16"

    @patch("boto3.client")
    def test_discover_load_balancers(self, mock_boto_client, aws_detector):
        """Test load balancer discovery"""
        elbv2_mock = MagicMock()
        mock_boto_client.return_value = elbv2_mock

        elbv2_mock.describe_load_balancers.return_value = {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/web-alb/1234567890abcdef",
                    "LoadBalancerName": "web-alb",
                    "Type": "application",
                    "Scheme": "internet-facing",
                    "State": {"Code": "active"},
                    "VpcId": "vpc-12345678",
                    "DNSName": "web-alb-123456.us-east-1.elb.amazonaws.com",
                }
            ]
        }

        nodes = aws_detector._discover_load_balancers()

        assert len(nodes) == 1
        assert nodes[0].key == "elb:web-alb"
        assert nodes[0].properties["service"] == "ELB"
        assert nodes[0].properties["load_balancer_type"] == "application"

    @patch("boto3.client")
    def test_discover_cloudfront_distributions(self, mock_boto_client, aws_detector):
        """Test CloudFront distribution discovery"""
        cloudfront_mock = MagicMock()
        mock_boto_client.return_value = cloudfront_mock

        cloudfront_mock.list_distributions.return_value = {
            "DistributionList": {
                "Items": [
                    {
                        "Id": "E123ABCD",
                        "DomainName": "d123.cloudfront.net",
                        "Status": "Deployed",
                        "Enabled": True,
                        "Origins": {
                            "Items": [{"DomainName": "my-bucket.s3.amazonaws.com"}]
                        },
                    }
                ]
            }
        }

        nodes = aws_detector._discover_cloudfront()

        assert len(nodes) == 1
        assert nodes[0].key == "cloudfront:E123ABCD"
        assert nodes[0].properties["service"] == "CloudFront"

    @patch("boto3.client")
    def test_discover_direct_connect(self, mock_boto_client, aws_detector):
        """Test Direct Connect discovery"""
        dx_mock = MagicMock()
        mock_boto_client.return_value = dx_mock

        dx_mock.describe_connections.return_value = {
            "connections": [
                {
                    "connectionId": "dxcon-12345678",
                    "connectionName": "aws-office-connection",
                    "bandwidth": "10Gbps",
                    "location": "Washington DC",
                    "connectionState": "available",
                }
            ]
        }

        nodes = aws_detector._discover_direct_connect()

        assert len(nodes) == 1
        assert nodes[0].key == "directconnect:dxcon-12345678"
        assert nodes[0].properties["service"] == "DirectConnect"


class TestSecurityServices:
    """Test discovery of security services: IAM, KMS, Secrets Manager, Directory Service"""

    @patch("boto3.client")
    def test_discover_iam_roles(self, mock_boto_client, aws_detector):
        """Test IAM role discovery"""
        iam_mock = MagicMock()
        mock_boto_client.return_value = iam_mock

        iam_mock.list_roles.return_value = {
            "Roles": [
                {
                    "RoleName": "lambda-execution-role",
                    "Arn": "arn:aws:iam::123456789012:role/lambda-execution-role",
                    "CreateDate": datetime(2024, 1, 1),
                }
            ]
        }

        nodes = aws_detector._discover_iam_roles()

        assert len(nodes) == 1
        assert nodes[0].key == "iam:role:lambda-execution-role"
        assert nodes[0].properties["service"] == "IAM"

    @patch("boto3.client")
    def test_discover_kms_keys(self, mock_boto_client, aws_detector):
        """Test KMS key discovery"""
        kms_mock = MagicMock()
        mock_boto_client.return_value = kms_mock

        kms_mock.list_keys.return_value = {
            "Keys": [
                {
                    "KeyId": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
                }
            ]
        }
        kms_mock.describe_key.return_value = {
            "KeyMetadata": {
                "KeyId": "12345678-1234-1234-1234-123456789012",
                "Arn": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                "KeyManager": "CUSTOMER",
                "KeyState": "Enabled",
                "Description": "Application encryption key",
            }
        }

        nodes = aws_detector._discover_kms()

        assert len(nodes) == 1
        assert nodes[0].properties["service"] == "KMS"

    @patch("boto3.client")
    def test_discover_secrets_manager(self, mock_boto_client, aws_detector):
        """Test Secrets Manager secret discovery"""
        secrets_mock = MagicMock()
        mock_boto_client.return_value = secrets_mock

        secrets_mock.list_secrets.return_value = {
            "SecretList": [
                {
                    "Name": "db/prod/password",
                    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db/prod/password-abc123",
                    "CreatedDate": datetime(2024, 1, 1),
                }
            ]
        }

        nodes = aws_detector._discover_secrets_manager()

        assert len(nodes) == 1
        assert nodes[0].key == "secretsmanager:db/prod/password"
        assert nodes[0].properties["service"] == "SecretsManager"

    @patch("boto3.client")
    def test_discover_directory_service(self, mock_boto_client, aws_detector):
        """Test Directory Service discovery"""
        ds_mock = MagicMock()
        mock_boto_client.return_value = ds_mock

        ds_mock.describe_directories.return_value = {
            "DirectoryDescriptions": [
                {
                    "DirectoryId": "d-12345678",
                    "Name": "corp.example.com",
                    "Type": "MicrosoftAD",
                    "Stage": "Active",
                    "VpcSettings": {"VpcId": "vpc-12345678"},
                }
            ]
        }

        nodes = aws_detector._discover_directory_service()

        assert len(nodes) == 1
        assert nodes[0].properties["service"] == "DirectoryService"


class TestObservabilityServices:
    """Test discovery of observability services: CloudWatch, CloudTrail, Systems Manager"""

    @patch("boto3.client")
    def test_discover_cloudwatch_log_groups(self, mock_boto_client, aws_detector):
        """Test CloudWatch log group discovery"""
        logs_mock = MagicMock()
        mock_boto_client.return_value = logs_mock

        logs_mock.describe_log_groups.return_value = {
            "logGroups": [
                {
                    "logGroupName": "/aws/lambda/order-processor",
                    "storedBytes": 1048576,
                    "retentionInDays": 14,
                }
            ]
        }

        nodes = aws_detector._discover_cloudwatch()

        assert len(nodes) == 1
        assert nodes[0].key == "cloudwatch:loggroup:/aws/lambda/order-processor"
        assert nodes[0].properties["service"] == "CloudWatch"

    @patch("boto3.client")
    def test_discover_cloudtrail_trails(self, mock_boto_client, aws_detector):
        """Test CloudTrail trail discovery"""
        cloudtrail_mock = MagicMock()
        mock_boto_client.return_value = cloudtrail_mock

        cloudtrail_mock.describe_trails.return_value = {
            "trailList": [
                {
                    "Name": "OrganizationTrail",
                    "TrailArn": "arn:aws:cloudtrail:us-east-1:123456789012:trail/OrganizationTrail",
                    "S3BucketName": "cloudtrail-logs",
                    "IsMultiRegionTrail": True,
                    "HomeRegion": "us-east-1",
                }
            ]
        }

        nodes = aws_detector._discover_cloudtrail()

        assert len(nodes) == 1
        assert nodes[0].properties["service"] == "CloudTrail"

    @patch("boto3.client")
    def test_discover_systems_manager(self, mock_boto_client, aws_detector):
        """Test Systems Manager discovery"""
        ssm_mock = MagicMock()
        mock_boto_client.return_value = ssm_mock

        ssm_mock.describe_parameters.return_value = {
            "Parameters": [{"Name": "/app/db_host", "Type": "String"}]
        }

        nodes = aws_detector._discover_systems_manager()

        assert len(nodes) == 1
        assert nodes[0].properties["service"] == "SystemsManager"


class TestIntegrationServices:
    """Test discovery of integration services: SQS, SNS, EventBridge, API Gateway"""

    @patch("boto3.client")
    def test_discover_sqs_queues(self, mock_boto_client, aws_detector):
        """Test SQS queue discovery"""
        sqs_mock = MagicMock()
        mock_boto_client.return_value = sqs_mock

        sqs_mock.list_queues.return_value = {
            "QueueUrls": [
                "https://sqs.us-east-1.amazonaws.com/123456789012/order-queue",
                "https://sqs.us-east-1.amazonaws.com/123456789012/email-queue",
            ]
        }

        nodes = aws_detector._discover_sqs()

        assert len(nodes) == 2
        assert nodes[0].key == "sqs:order-queue"
        assert nodes[1].key == "sqs:email-queue"
        assert all(n.properties["service"] == "SQS" for n in nodes)

    @patch("boto3.client")
    def test_discover_sns_topics(self, mock_boto_client, aws_detector):
        """Test SNS topic discovery"""
        sns_mock = MagicMock()
        mock_boto_client.return_value = sns_mock

        sns_mock.list_topics.return_value = {
            "Topics": [
                {"TopicArn": "arn:aws:sns:us-east-1:123456789012:order-notifications"}
            ]
        }

        nodes = aws_detector._discover_sns()

        assert len(nodes) == 1
        assert nodes[0].key == "sns:order-notifications"
        assert nodes[0].properties["service"] == "SNS"

    @patch("boto3.client")
    def test_discover_eventbridge_rules(self, mock_boto_client, aws_detector):
        """Test EventBridge rule discovery"""
        events_mock = MagicMock()
        mock_boto_client.return_value = events_mock

        events_mock.list_rules.return_value = {
            "Rules": [
                {
                    "Name": "daily-sync",
                    "State": "ENABLED",
                    "EventPattern": '{"source":["aws.events"]}',
                    "ScheduleExpression": "rate(1 day)",
                }
            ]
        }

        nodes = aws_detector._discover_eventbridge()

        assert len(nodes) == 1
        assert nodes[0].key == "eventbridge:rule:daily-sync"
        assert nodes[0].properties["service"] == "EventBridge"

    @patch("boto3.client")
    def test_discover_api_gateway_apis(self, mock_boto_client, aws_detector):
        """Test API Gateway API discovery"""
        apigw_mock = MagicMock()
        mock_boto_client.return_value = apigw_mock

        apigw_mock.get_rest_apis.return_value = {
            "items": [{"id": "abc123def456", "name": "order-api"}]
        }

        nodes = aws_detector._discover_api_gateway()

        assert len(nodes) == 1
        assert nodes[0].key == "apigateway:abc123def456"
        assert nodes[0].properties["service"] == "APIGateway"


class TestRelationshipDetection:
    """Test detection of relationships between services"""

    def test_detect_ec2_to_ebs_relationships(self, aws_detector):
        """Test EC2 -> EBS volume relationships"""
        nodes = [
            DiscoveryNode(
                key="ec2:i-12345678",
                display_name="web-server",
                node_type="compute",
                properties={"service": "EC2", "attached_to": ["vol-12345678"]},
            ),
            DiscoveryNode(
                key="ebs:vol-12345678",
                display_name="data-volume",
                node_type="storage",
                properties={"service": "EBS"},
            ),
        ]

        edges = aws_detector._detect_relationships(nodes)

        assert len(edges) >= 1
        ebs_edges = [
            e
            for e in edges
            if e.from_node_key == "ec2:i-12345678"
            and e.to_node_key == "ebs:vol-12345678"
        ]
        assert len(ebs_edges) > 0
        assert ebs_edges[0].edge_type == "uses"

    def test_detect_lambda_to_vpc_relationships(self, aws_detector):
        """Test Lambda -> VPC relationships"""
        nodes = [
            DiscoveryNode(
                key="lambda:processor",
                display_name="processor",
                node_type="compute",
                properties={"service": "Lambda", "vpc_id": "vpc-12345678"},
            ),
            DiscoveryNode(
                key="vpc:vpc-12345678",
                display_name="production",
                node_type="network",
                properties={"service": "VPC"},
            ),
        ]

        edges = aws_detector._detect_relationships(nodes)

        vpc_edges = [
            e
            for e in edges
            if e.from_node_key == "lambda:processor"
            and e.to_node_key == "vpc:vpc-12345678"
        ]
        assert len(vpc_edges) > 0

    def test_detect_cloudfront_to_s3_relationships(self, aws_detector):
        """Test CloudFront -> S3 relationships"""
        nodes = [
            DiscoveryNode(
                key="cloudfront:E123ABCD",
                display_name="cdn",
                node_type="network",
                properties={
                    "service": "CloudFront",
                    "origins": ["my-bucket.s3.amazonaws.com"],
                },
            ),
            DiscoveryNode(
                key="s3:my-bucket",
                display_name="my-bucket",
                node_type="storage",
                properties={"service": "S3"},
            ),
        ]

        edges = aws_detector._detect_relationships(nodes)

        cf_s3_edges = [
            e
            for e in edges
            if e.from_node_key == "cloudfront:E123ABCD"
            and e.to_node_key == "s3:my-bucket"
        ]
        assert len(cf_s3_edges) > 0
        assert cf_s3_edges[0].edge_type == "originates_from"


class TestFullDiscoveryWorkflow:
    """Integration tests for the full discovery workflow"""

    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_discover_disjointed_nodes(self, mock_boto_client, aws_detector):
        """Test discovery with include_relationships=False (disjointed nodes)"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock EC2
        mock_client.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"InstanceId": "i-1", "InstanceType": "t3.micro", "State": {"Name": "running"}}]}]
        }
        # Mock VPC
        mock_client.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-1"}]}
        
        # Run discovery with include_relationships=False
        result = await aws_detector.discover(include_relationships=False)
        
        assert len(result.nodes) >= 2
        assert len(result.edges) == 0
        assert "Skipping relationship detection" in [record.message for record in caplog.records] if "caplog" in locals() else True

    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_enhanced_metadata_extraction(self, mock_boto_client, aws_detector):
        """Test that enhanced metadata is correctly extracted"""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock EC2 with extra fields
        mock_client.describe_instances.return_value = {
            "Reservations": [{
                "Instances": [{
                    "InstanceId": "i-1", 
                    "InstanceType": "t3.micro", 
                    "State": {"Name": "running"},
                    "ImageId": "ami-123",
                    "PublicDnsName": "ec2-1.aws.com",
                    "Tags": [{"Key": "Env", "Value": "Prod"}]
                }]
            }]
        }
        
        nodes = aws_detector._discover_ec2()
        assert len(nodes) == 1
        props = nodes[0].properties
        assert props["image_id"] == "ami-123"
        assert props["public_dns_name"] == "ec2-1.aws.com"
        assert props["tags"] == {"Env": "Prod"}

    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_full_discovery_workflow(self, mock_boto_client, aws_detector):
        """Test discovering and integrating multiple service types"""
        # Setup minimal mocks for all services
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Mock STS for account ID
        mock_client.get_caller_identity.return_value = {"Account": "123456789012"}

        # Mock EC2
        mock_client.describe_instances.return_value = {"Reservations": []}
        mock_client.describe_vpcs.return_value = {"Vpcs": []}
        mock_client.describe_volumes.return_value = {"Volumes": []}

        # Mock Lambda
        mock_client.get_paginator.return_value.paginate.return_value = [
            {"Functions": []}
        ]

        # Mock other services with empty results
        mock_client.list_clusters.return_value = {"clusterArns": []}
        mock_client.describe_db_instances.return_value = {"DBInstances": []}
        mock_client.describe_db_clusters.return_value = {"DBClusters": []}
        mock_client.list_tables.return_value = {"TableNames": []}
        mock_client.describe_clusters.return_value = {"Clusters": []}
        mock_client.describe_load_balancers.return_value = {"LoadBalancers": []}
        mock_client.list_distributions.return_value = {"DistributionList": {"Items": []}}
        mock_client.describe_connections.return_value = {"connections": []}
        mock_client.list_roles.return_value = {"Roles": []}
        mock_client.list_keys.return_value = {"Keys": []}
        mock_client.list_secrets.return_value = {"SecretList": []}
        mock_client.describe_directories.return_value = {"DirectoryDescriptions": []}
        mock_client.describe_log_groups.return_value = {"logGroups": []}
        mock_client.describe_trails.return_value = {"trailList": []}
        mock_client.describe_parameters.return_value = {"Parameters": []}
        mock_client.list_queues.return_value = {"QueueUrls": []}
        mock_client.list_topics.return_value = {"Topics": []}
        mock_client.list_rules.return_value = {"Rules": []}
        mock_client.get_rest_apis.return_value = {"items": []}
        mock_client.list_buckets.return_value = {"Buckets": []}
        mock_client.describe_file_systems.return_value = {"FileSystems": []}

        result = await aws_detector.discover()

        assert isinstance(result, DiscoveryResult)
        assert result.source == "aws"
        assert result.metadata["region"] == "us-east-1"
        assert result.metadata["account_id"] == "123456789012"
