"""
Unit tests for AWS Compute Services: EC2, Lambda, ECS, EKS

These tests verify that the detector correctly identifies compute resources
with proper attributes and properties.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from apps.api.ingestors.aws.detector import AWSDetector


class TestEC2Discovery:
    """Test EC2 instance discovery"""

    @patch("boto3.client")
    def test_discover_ec2_instances(self, mock_boto_client, aws_detector):
        """Test EC2 instance discovery with complete properties"""
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
        assert nodes[0].properties["state"] == "running"

    @patch("boto3.client")
    def test_discover_ec2_multiple_instances(self, mock_boto_client, aws_detector):
        """Test EC2 discovery with multiple instances"""
        ec2_mock = MagicMock()
        mock_boto_client.return_value = ec2_mock

        ec2_mock.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": f"i-{i:017d}",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": f"10.0.0.{10+i}",
                            "VpcId": "vpc-12345678",
                            "Placement": {"AvailabilityZone": "us-east-1a"},
                            "SecurityGroups": [],
                            "Tags": [{"Key": "Name", "Value": f"server-{i}"}],
                        }
                        for i in range(3)
                    ]
                }
            ]
        }

        nodes = aws_detector._discover_ec2()

        assert len(nodes) == 3
        assert all(n.properties["service"] == "EC2" for n in nodes)
        assert all(n.node_type == "compute" for n in nodes)


class TestLambdaDiscovery:
    """Test Lambda function discovery"""

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
        assert nodes[0].properties["timeout"] == 30

    @patch("boto3.client")
    def test_discover_lambda_no_vpc(self, mock_boto_client, aws_detector):
        """Test Lambda discovery without VPC configuration"""
        lambda_mock = MagicMock()
        mock_boto_client.return_value = lambda_mock

        lambda_mock.get_paginator.return_value.paginate.return_value = [
            {
                "Functions": [
                    {
                        "FunctionName": "simple-function",
                        "Runtime": "python3.11",
                        "MemorySize": 128,
                        "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:simple-function",
                    }
                ]
            }
        ]

        nodes = aws_detector._discover_lambda()

        assert len(nodes) == 1
        assert nodes[0].properties.get("vpc_id") is None


class TestECSDiscovery:
    """Test ECS cluster and service discovery"""

    @patch("boto3.client")
    def test_discover_ecs_clusters_and_services(self, mock_boto_client, aws_detector):
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
    def test_discover_ecs_no_resources(self, mock_boto_client, aws_detector):
        """Test ECS discovery with no clusters"""
        ecs_mock = MagicMock()
        mock_boto_client.return_value = ecs_mock

        ecs_mock.list_clusters.return_value = {"clusterArns": []}

        nodes = aws_detector._discover_ecs()

        assert len(nodes) == 0


class TestEKSDiscovery:
    """Test EKS cluster discovery"""

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
        assert nodes[0].properties["status"] == "ACTIVE"

    @patch("boto3.client")
    def test_discover_eks_multiple_clusters(self, mock_boto_client, aws_detector):
        """Test EKS discovery with multiple clusters"""
        eks_mock = MagicMock()
        mock_boto_client.return_value = eks_mock

        eks_mock.list_clusters.return_value = {
            "clusters": ["prod-cluster", "staging-cluster"]
        }
        eks_mock.describe_cluster.side_effect = [
            {
                "cluster": {
                    "name": "prod-cluster",
                    "version": "1.27",
                    "status": "ACTIVE",
                    "arn": "arn:aws:eks:us-east-1:123456789012:cluster/prod-cluster",
                }
            },
            {
                "cluster": {
                    "name": "staging-cluster",
                    "version": "1.26",
                    "status": "ACTIVE",
                    "arn": "arn:aws:eks:us-east-1:123456789012:cluster/staging-cluster",
                }
            },
        ]

        nodes = aws_detector._discover_eks()

        assert len(nodes) == 2
        assert any(n.key == "eks:prod-cluster" for n in nodes)
        assert any(n.key == "eks:staging-cluster" for n in nodes)
