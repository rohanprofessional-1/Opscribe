# Test Suite Organization

This directory contains the organized test suite for Opscribe infrastructure discovery. Tests are split into **unit tests** and **integration tests**, with each focused on specific aspects of the system.

## Directory Structure

```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Root pytest config (shared fixtures)
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── conftest.py                # Unit test fixtures
│   └── discovery/
│       ├── __init__.py
│       ├── conftest.py            # Discovery-specific fixtures
│       ├── test_aws_detector_compute.py      # EC2, Lambda, ECS, EKS tests
│       ├── test_aws_detector_storage.py      # S3, EBS, EFS, FSx tests
│       ├── test_aws_detector_database.py     # RDS, DynamoDB, Redshift tests
│       ├── test_aws_detector_networking.py   # VPC, ELB, CloudFront, DirectConnect tests
│       ├── test_aws_detector_security.py     # IAM, KMS, Secrets Manager tests
│       ├── test_aws_detector_observability.py # CloudWatch, CloudTrail, Systems Manager tests
│       ├── test_aws_detector_integration.py   # SQS, SNS, EventBridge, API Gateway tests
│       └── test_aws_detector_relationships.py # Relationship detection tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   └── discovery/
│       ├── __init__.py
│       ├── conftest.py            # Integration test fixtures
│       ├── test_mock_cluster_setup.py         # Mock infrastructure tests
│       ├── test_detector_with_mock_cluster.py # Detector with realistic mock data
│       └── test_cluster_scenarios.py          # Complex scenario tests
└── fixtures/                      # Test fixtures and helpers
    ├── __init__.py
    └── mock_aws_cluster.py        # MockAWSCluster factory
```

## Test Categories

### Unit Tests (`tests/unit/discovery/`)

Unit tests verify individual detection methods in isolation using **mocked boto3 responses**.

**Coverage by service category:**

- **`test_aws_detector_compute.py`** (4 test classes)
  - EC2 instances, Lambda functions, ECS clusters/services, EKS clusters
  - Tests: `TestEC2Discovery`, `TestLambdaDiscovery`, `TestECSDiscovery`, `TestEKSDiscovery`

- **`test_aws_detector_storage.py`** (4 test classes)
  - S3 buckets, EBS volumes, EFS file systems, FSx file systems
  - Tests: `TestS3Discovery`, `TestEBSDiscovery`, `TestEFSDiscovery`, `TestFSxDiscovery`

- **`test_aws_detector_database.py`** (3 test classes)
  - RDS instances, DynamoDB tables, Redshift clusters
  - Tests: `TestRDSDiscovery`, `TestDynamoDBDiscovery`, `TestRedshiftDiscovery`

- **`test_aws_detector_networking.py`** (4 test classes)
  - VPCs, Load Balancers, CloudFront distributions, Direct Connect connections
  - Tests: `TestVPCDiscovery`, `TestLoadBalancerDiscovery`, `TestCloudFrontDiscovery`, `TestDirectConnectDiscovery`

- **`test_aws_detector_security.py`** (4 test classes)
  - IAM roles, KMS keys, Secrets Manager, Directory Service
  - Tests: `TestIAMDiscovery`, `TestKMSDiscovery`, `TestSecretsManagerDiscovery`, `TestDirectoryServiceDiscovery`

- **`test_aws_detector_observability.py`** (3 test classes)
  - CloudWatch log groups, CloudTrail trails, Systems Manager parameters
  - Tests: `TestCloudWatchDiscovery`, `TestCloudTrailDiscovery`, `TestSystemsManagerDiscovery`

- **`test_aws_detector_integration.py`** (4 test classes)
  - SQS queues, SNS topics, EventBridge rules, API Gateway APIs
  - Tests: `TestSQSDiscovery`, `TestSNSDiscovery`, `TestEventBridgeDiscovery`, `TestAPIGatewayDiscovery`

- **`test_aws_detector_relationships.py`** (3 test classes)
  - EC2 → EBS relationships, Lambda → VPC relationships, CloudFront → S3 relationships
  - Tests: `TestEC2EBSRelationships`, `TestLambdaVPCRelationships`, `TestCloudFrontS3Relationships`

**Running unit tests:**

```bash
# All unit tests
pytest tests/unit/discovery/ -v

# Specific service category
pytest tests/unit/discovery/test_aws_detector_compute.py -v

# Single test
pytest tests/unit/discovery/test_aws_detector_compute.py::TestEC2Discovery::test_discover_ec2_instances -v
```

### Integration Tests (`tests/integration/discovery/`)

Integration tests verify the detector against **realistic mock infrastructure** without real AWS accounts.

**Test files:**

- **`test_mock_cluster_setup.py`** (9 tests)
  - Verifies MockAWSCluster factory creates valid AWS resource structures
  - Tests: `TestMockClusterSetup`
  - Coverage: VPC, subnets, EC2, RDS, S3, SQS structure validation

- **`test_detector_with_mock_cluster.py`** (7 tests)
  - Tests detector discovery against realistic mock infrastructure
  - Tests: `TestDetectorWithMockCluster`
  - Coverage: Service discovery, node properties, relationships, tag consistency

- **`test_cluster_scenarios.py`** (7 tests)
  - Tests realistic infrastructure scenarios
  - Tests: `TestClusterScenarios`
  - Coverage: Multi-AZ deployments, distributed resources, relationship detection

**Running integration tests:**

```bash
# All integration tests
pytest tests/integration/discovery/ -v

# Specific test file
pytest tests/integration/discovery/test_mock_cluster_setup.py -v

# Single test
pytest tests/integration/discovery/test_detector_with_mock_cluster.py::TestDetectorWithMockCluster::test_detector_finds_correct_ec2_instances -v
```

### Test Fixtures

**Root fixtures** (`tests/conftest.py`):

- `aws_detector`: Basic AWSDetector instance for unit tests

**Unit test fixtures** (`tests/unit/discovery/conftest.py`):

- `aws_detector`: AWSDetector instance

**Integration test fixtures** (`tests/integration/discovery/conftest.py`):

- `mock_cluster`: MockAWSCluster instance for realistic infrastructure
- `mocked_aws_detector`: Fully mocked AWSDetector with boto3 routing to mock cluster data

**Mock Infrastructure** (`tests/fixtures/mock_aws_cluster.py`):

- `MockAWSCluster`: Factory creating realistic mock AWS infrastructure
  - Includes: VPC, 2 subnets (multi-AZ), 2 EC2 instances, RDS, S3, SQS
  - All resources properly tagged for testing consistency
  - Deterministic ID generation for reproducible tests

## Running Tests

### All tests

```bash
pytest tests/ -v
```

### Unit tests only

```bash
pytest tests/unit/ -v
```

### Integration tests only

```bash
pytest tests/integration/ -v
```

### By service category

```bash
pytest tests/unit/discovery/test_aws_detector_compute.py -v
pytest tests/unit/discovery/test_aws_detector_storage.py -v
pytest tests/unit/discovery/test_aws_detector_database.py -v
```

### With coverage report

```bash
pytest tests/ --cov=apps/api/infrastructure/discovery --cov-report=html
```

### Quick run (parallel)

```bash
pytest tests/ -n auto
```

## Test Statistics

- **Total Test Files**: 12
- **Total Test Classes**: 35+
- **Unit Tests**: ~60+
- **Integration Tests**: 23
- **Total Tests**: 85+

### Coverage by Service Category

| Category      | Services                                     | Tests |
| ------------- | -------------------------------------------- | ----- |
| Compute       | EC2, Lambda, ECS, EKS                        | 15+   |
| Storage       | S3, EBS, EFS, FSx                            | 15+   |
| Database      | RDS, DynamoDB, Redshift                      | 12+   |
| Networking    | VPC, ELB, CloudFront, DirectConnect          | 15+   |
| Security      | IAM, KMS, Secrets Manager, Directory Service | 15+   |
| Observability | CloudWatch, CloudTrail, Systems Manager      | 12+   |
| Integration   | SQS, SNS, EventBridge, API Gateway           | 15+   |
| Relationships | EC2↔EBS, Lambda↔VPC, CloudFront↔S3           | 8+    |

## Writing New Tests

### Unit Test Template

```python
"""Tests for a specific AWS service."""

import pytest
from unittest.mock import patch, MagicMock
from infrastructure.discovery.detectors.aws import AWSDetector


class TestServiceDiscovery:
    """Test ServiceName discovery"""

    @patch('boto3.client')
    def test_discover_resource(self, mock_boto_client, aws_detector):
        """Test resource discovery"""
        service_mock = MagicMock()
        mock_boto_client.return_value = service_mock

        # Setup mock response
        service_mock.list_resources.return_value = {...}

        # Call detector method
        nodes = aws_detector._discover_service()

        # Assertions
        assert len(nodes) == 1
        assert nodes[0].key == "service:resource-id"
        assert nodes[0].properties["service"] == "ServiceName"
```

### Integration Test Template

```python
"""Tests for detector with mock infrastructure."""

import pytest


class TestServiceIntegration:
    """Test service discovery with mock cluster"""

    @pytest.mark.asyncio
    async def test_detector_finds_resource(self, mocked_aws_detector):
        """Test resource discovery"""
        detector, mock_cluster = mocked_aws_detector

        result = await detector.discover()

        # Find specific nodes
        nodes = [n for n in result.nodes if n.properties.get("service") == "Service"]

        # Assertions
        assert len(nodes) > 0
        assert nodes[0].key == "service:resource-id"
```

## CI/CD Integration

These tests are ready for CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run unit tests
  run: pytest tests/unit/ -v --tb=short

- name: Run integration tests
  run: pytest tests/integration/ -v --tb=short

- name: Generate coverage
  run: pytest tests/ --cov=apps/api/infrastructure/discovery --cov-report=xml
```

## Notes

- Unit tests are **fast** (~5-10 seconds) and **isolated** with mocked responses
- Integration tests are **realistic** using MockAWSCluster but still **fast** (~2-5 seconds)
- All tests are **independent** and can run in any order
- Fixtures use **pytest-asyncio** for async test support
- Mock infrastructure is **deterministic** for reproducible results
