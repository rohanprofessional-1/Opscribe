"""
Integration tests for mock AWS cluster setup.

These tests verify that the mock cluster factory creates realistic,
properly structured AWS resource representations.
"""

import pytest


class TestMockClusterSetup:
    """Test the mock cluster factory itself"""

    def test_cluster_creation(self, mock_cluster):
        """Test that we can create a mock cluster"""
        assert mock_cluster.service_name == "opscribe-test"
        assert mock_cluster.vpc_id.startswith("vpc-")
        assert len(mock_cluster.subnet_ids) == 2

    def test_cluster_summary(self, mock_cluster):
        """Test cluster summary contains all expected components"""
        summary = mock_cluster.summary()

        assert summary["service_name"] == "opscribe-test"
        assert summary["account_id"] == "123456789012"
        assert summary["region"] == "us-east-1"

        # Check VPC
        assert "vpc" in summary
        assert summary["vpc"]["cidr"] == "10.0.0.0/16"

        # Check subnets
        assert len(summary["subnets"]) == 2
        assert summary["subnets"][0]["cidr"] == "10.0.1.0/24"
        assert summary["subnets"][1]["cidr"] == "10.0.2.0/24"

        # Check EC2
        assert len(summary["ec2_instances"]) == 2

        # Check RDS
        assert summary["rds"]["engine"] == "postgres"

        # Check S3
        assert summary["s3"]["bucket_name"] == "opscribe-test-terraform-state"

        # Check SQS
        assert summary["sqs"]["queue_name"] == "opscribe-test-events"

    def test_vpc_structure(self, mock_cluster):
        """Test VPC mock data structure"""
        vpc = mock_cluster.vpc()

        assert vpc["VpcId"] == mock_cluster.vpc_id
        assert vpc["CidrBlock"] == "10.0.0.0/16"
        assert vpc["State"] == "available"
        assert any(t["Key"] == "Service" for t in vpc["Tags"])

    def test_subnets_structure(self, mock_cluster):
        """Test subnet mock data structure"""
        subnets = mock_cluster.subnets()

        assert len(subnets) == 2

        # First subnet in AZ a
        assert subnets[0]["SubnetId"] == mock_cluster.subnet_ids[0]
        assert subnets[0]["VpcId"] == mock_cluster.vpc_id
        assert subnets[0]["CidrBlock"] == "10.0.1.0/24"
        assert subnets[0]["AvailabilityZone"] == "us-east-1a"

        # Second subnet in AZ b
        assert subnets[1]["SubnetId"] == mock_cluster.subnet_ids[1]
        assert subnets[1]["AvailabilityZone"] == "us-east-1b"

    def test_ec2_instances_structure(self, mock_cluster):
        """Test EC2 instance mock data structure"""
        instances = mock_cluster.ec2_instances()

        assert len(instances) == 2

        # First instance in first subnet
        assert instances[0]["InstanceId"] == mock_cluster.ec2_instance_ids[0]
        assert instances[0]["InstanceType"] == "t3.medium"
        assert instances[0]["State"]["Name"] == "running"
        assert instances[0]["PrivateIpAddress"] == "10.0.1.10"
        assert instances[0]["SubnetId"] == mock_cluster.subnet_ids[0]
        assert instances[0]["VpcId"] == mock_cluster.vpc_id

        # Second instance in second subnet
        assert instances[1]["InstanceId"] == mock_cluster.ec2_instance_ids[1]
        assert instances[1]["PrivateIpAddress"] == "10.0.2.10"
        assert instances[1]["SubnetId"] == mock_cluster.subnet_ids[1]

    def test_rds_instance_structure(self, mock_cluster):
        """Test RDS instance mock data structure"""
        rds = mock_cluster.rds_instance()

        assert rds["DBInstanceIdentifier"] == mock_cluster.rds_instance_id
        assert rds["Engine"] == "postgres"
        assert rds["DBInstanceClass"] == "db.t3.micro"
        assert rds["DBInstanceStatus"] == "available"

    def test_s3_bucket_structure(self, mock_cluster):
        """Test S3 bucket mock data structure"""
        bucket = mock_cluster.s3_bucket()

        assert bucket["Name"] == mock_cluster.s3_bucket_name
        assert "CreationDate" in bucket
        assert "Tags" in bucket
        assert any(t["Key"] == "Service" for t in bucket["Tags"])

    def test_sqs_queue_structure(self, mock_cluster):
        """Test SQS queue mock data structure"""
        queue_url = mock_cluster.sqs_queue()

        assert mock_cluster.sqs_queue_name in queue_url
        assert "sqs" in queue_url
        assert mock_cluster.region in queue_url
        assert mock_cluster.account_id in queue_url

    def test_deterministic_id_generation(self, mock_cluster):
        """Test that ID generation is deterministic"""
        # Create another cluster with the same service name
        mock_cluster2 = type(mock_cluster)(service_name=mock_cluster.service_name)

        # IDs should be identical for same service name
        assert mock_cluster.vpc_id == mock_cluster2.vpc_id
        assert mock_cluster.subnet_ids == mock_cluster2.subnet_ids
        assert mock_cluster.ec2_instance_ids == mock_cluster2.ec2_instance_ids

    def test_unique_ids_per_cluster(self, mock_cluster):
        """Test that clusters have unique IDs"""
        # Create another cluster with different service name
        mock_cluster2 = type(mock_cluster)(service_name="different-service")

        # IDs should be different for different service names
        assert mock_cluster.vpc_id != mock_cluster2.vpc_id
        assert mock_cluster.subnet_ids != mock_cluster2.subnet_ids
