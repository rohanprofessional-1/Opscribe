"""
Integration tests using mock AWS cluster data.

These tests verify that the detector correctly identifies and
relationships between resources in a realistic infrastructure setup.
"""

import pytest
from .mock_aws_cluster import MockAWSCluster
from apps.api.ingestors.aws.detector import AWSDetector


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
        assert rds["DBInstanceStatus"] == "available"
        assert rds["DBInstanceClass"] == "db.t3.micro"
        assert mock_cluster.vpc_id in rds["DBSubnetGroup"]["VpcId"]

    def test_s3_bucket_structure(self, mock_cluster):
        """Test S3 bucket mock data structure"""
        bucket = mock_cluster.s3_bucket()

        assert bucket["Name"] == mock_cluster.s3_bucket_name
        assert "opscribe-test" in bucket["Name"]

    def test_s3_bucket_with_terraform_state(self, mock_cluster):
        """Test S3 bucket with Terraform state file"""
        bucket = mock_cluster.s3_bucket_with_terraform_state()

        assert "Contents" in bucket
        assert len(bucket["Contents"]) > 0

        # Check for terraform state file
        terraform_files = [c for c in bucket["Contents"] if "terraform" in c["Key"]]
        assert len(terraform_files) > 0
        assert terraform_files[0]["Key"] == "terraform/state/main.tfstate"

    def test_sqs_queue_structure(self, mock_cluster):
        """Test SQS queue mock data structure"""
        queue_url = mock_cluster.sqs_queue()

        assert mock_cluster.sqs_queue_name in queue_url
        assert "sqs" in queue_url
        assert mock_cluster.account_id in queue_url


class TestDetectorWithMockCluster:
    """Test the AWSDetector with mock cluster data"""

    @pytest.mark.asyncio
    async def test_detector_discovers_mock_cluster(self, mocked_aws_detector):
        """Test that detector correctly identifies all resources in mock cluster"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Check that we got results
        assert len(result.nodes) > 0
        assert result.source == "aws"

        # Count resources by service
        services_found = {}
        for node in result.nodes:
            service = node.properties.get("service", "Unknown")
            services_found[service] = services_found.get(service, 0) + 1

        # Verify expected services are found
        assert "VPC" in services_found
        assert "EC2" in services_found
        assert "RDS" in services_found
        assert "S3" in services_found
        assert "SQS" in services_found

    @pytest.mark.asyncio
    async def test_detector_finds_correct_ec2_instances(self, mocked_aws_detector):
        """Test EC2 discovery finds both instances from mock cluster"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find EC2 nodes
        ec2_nodes = [n for n in result.nodes if n.properties.get("service") == "EC2"]

        assert len(ec2_nodes) >= 2, "Should find at least 2 EC2 instances"

        # Verify instance details
        instance_ids = [n.key for n in ec2_nodes]
        assert f"ec2:{mock_cluster.ec2_instance_ids[0]}" in instance_ids
        assert f"ec2:{mock_cluster.ec2_instance_ids[1]}" in instance_ids

    @pytest.mark.asyncio
    async def test_detector_finds_rds_instance(self, mocked_aws_detector):
        """Test RDS discovery finds the database"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find RDS nodes
        rds_nodes = [n for n in result.nodes if n.properties.get("service") == "RDS"]

        assert len(rds_nodes) >= 1, "Should find at least 1 RDS instance"
        assert rds_nodes[0].key == f"rds:{mock_cluster.rds_instance_id}"

    @pytest.mark.asyncio
    async def test_detector_finds_vpc(self, mocked_aws_detector):
        """Test VPC discovery finds the VPC"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find VPC nodes
        vpc_nodes = [n for n in result.nodes if n.properties.get("service") == "VPC"]

        assert len(vpc_nodes) >= 1, "Should find at least 1 VPC"
        assert vpc_nodes[0].key == f"vpc:{mock_cluster.vpc_id}"

    @pytest.mark.asyncio
    async def test_detector_finds_s3_bucket(self, mocked_aws_detector):
        """Test S3 discovery finds the bucket"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find S3 nodes
        s3_nodes = [n for n in result.nodes if n.properties.get("service") == "S3"]

        assert len(s3_nodes) >= 1, "Should find at least 1 S3 bucket"
        assert s3_nodes[0].key == f"s3:{mock_cluster.s3_bucket_name}"

    @pytest.mark.asyncio
    async def test_detector_finds_sqs_queue(self, mocked_aws_detector):
        """Test SQS discovery finds the queue"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find SQS nodes
        sqs_nodes = [n for n in result.nodes if n.properties.get("service") == "SQS"]

        assert len(sqs_nodes) >= 1, "Should find at least 1 SQS queue"
        assert sqs_nodes[0].key == f"sqs:{mock_cluster.sqs_queue_name}"

    @pytest.mark.asyncio
    async def test_detector_detects_ec2_to_vpc_relationships(self, mocked_aws_detector):
        """Test that detector finds VPC -> EC2 relationships"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find VPC to EC2 edges (VPC contains EC2)
        vpc_ec2_edges = [
            e for e in result.edges
            if "vpc:" in e.from_node_key and "ec2:" in e.to_node_key
        ]

        # We should find some VPC -> EC2 relationships
        assert len(vpc_ec2_edges) > 0, "Should detect VPC to EC2 relationships"

    @pytest.mark.asyncio
    async def test_detector_creates_nodes_with_correct_properties(self, mocked_aws_detector):
        """Test that detected nodes have correct properties"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Check EC2 node properties
        ec2_nodes = [n for n in result.nodes if n.properties.get("service") == "EC2"]
        if ec2_nodes:
            ec2_node = ec2_nodes[0]
            assert "instance_type" in ec2_node.properties
            assert "state" in ec2_node.properties
            assert "private_ip" in ec2_node.properties
            assert "vpc_id" in ec2_node.properties

        # Check RDS node properties
        rds_nodes = [n for n in result.nodes if n.properties.get("service") == "RDS"]
        if rds_nodes:
            rds_node = rds_nodes[0]
            assert "engine" in rds_node.properties
            assert "status" in rds_node.properties

        # Check VPC node properties
        vpc_nodes = [n for n in result.nodes if n.properties.get("service") == "VPC"]
        if vpc_nodes:
            vpc_node = vpc_nodes[0]
            assert "cidr_block" in vpc_node.properties

    @pytest.mark.asyncio
    async def test_detector_tags_consistency(self, mocked_aws_detector):
        """Test that all resources are tagged consistently"""
        detector, mock_cluster = mocked_aws_detector

        # All resources should have Service tag set to service_name
        resources = {
            "VPC": mock_cluster.vpc(),
            "EC2": mock_cluster.ec2_instances()[0],
            "RDS": mock_cluster.rds_instance(),
            "S3": mock_cluster.s3_bucket(),
        }

        for key, obj in resources.items():
            # Handle different tag key names (Tags vs TagList)
            tags = obj.get("Tags") or obj.get("TagList", [])
            service_tags = [t for t in tags if t.get("Key") == "Service"]
            assert len(service_tags) > 0, f"{key} should have Service tag"
            assert service_tags[0]["Value"] == "opscribe-test"


class TestClusterScenarios:
    """Test realistic infrastructure scenarios"""

    def test_multi_az_deployment(self, mock_cluster):
        """Test that cluster simulates multi-AZ deployment"""
        subnets = mock_cluster.subnets()
        azs = [s["AvailabilityZone"] for s in subnets]

        # Should have subnets in different AZs
        assert len(set(azs)) > 1, "Should have subnets in multiple AZs"
        assert "us-east-1a" in azs
        assert "us-east-1b" in azs

    def test_ec2_distribution_across_subnets(self, mock_cluster):
        """Test EC2 instances are distributed across subnets"""
        instances = mock_cluster.ec2_instances()
        subnet_distribution = {}

        for instance in instances:
            subnet_id = instance["SubnetId"]
            subnet_distribution[subnet_id] = subnet_distribution.get(subnet_id, 0) + 1

        # Should have instances in different subnets
        assert len(subnet_distribution) > 1, "Instances should be in different subnets"

    def test_database_in_subnet_group(self, mock_cluster):
        """Test RDS is properly configured in subnet group"""
        rds = mock_cluster.rds_instance()
        subnet_group = rds["DBSubnetGroup"]

        # Should reference all subnets
        assert subnet_group["VpcId"] == mock_cluster.vpc_id
        assert len(subnet_group["Subnets"]) > 0

    def test_terraform_state_in_s3(self, mock_cluster):
        """Test S3 bucket contains Terraform state file"""
        bucket = mock_cluster.s3_bucket_with_terraform_state()

        # Should have terraform state file
        assert "Contents" in bucket
        files = [c["Key"] for c in bucket["Contents"]]
        assert any("tfstate" in f for f in files)

    def test_consistent_naming(self, mock_cluster):
        """Test all resources follow consistent naming convention"""
        service_name = mock_cluster.service_name

        # Check VPC name tag
        vpc = mock_cluster.vpc()
        vpc_names = [t["Value"] for t in vpc["Tags"] if t["Key"] == "Name"]
        assert any(service_name in name for name in vpc_names)

        # Check S3 bucket name
        assert service_name in mock_cluster.s3_bucket_name

        # Check SQS queue name
        assert service_name in mock_cluster.sqs_queue_name

        # Check RDS identifier
        assert service_name in mock_cluster.rds_instance_id
