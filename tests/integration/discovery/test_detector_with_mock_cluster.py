"""
Integration tests for AWS detector with mock cluster.

These tests verify that the detector correctly processes mock infrastructure
and creates proper nodes and edges.
"""

import pytest


class TestDetectorWithMockCluster:
    """Test detector functionality against mock infrastructure"""

    @pytest.mark.asyncio
    async def test_detector_discovers_mock_cluster(self, mocked_aws_detector):
        """Test full discovery of mock cluster resources"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Verify result structure
        assert len(result.nodes) > 0
        assert len(result.metadata) > 0

    @pytest.mark.asyncio
    async def test_detector_finds_all_service_types(self, mocked_aws_detector):
        """Test that detector finds all service types in mock cluster"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Count services found
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
