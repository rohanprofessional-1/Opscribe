import pytest
import asyncio
from unittest.mock import MagicMock, patch
from apps.api.ingestors.pipeline.ingestors import AWSIngestor
from apps.api.ingestors.aws.schema import TopologyScan, TopologyNode

@pytest.mark.anyio
async def test_aws_ingestor_success():
    # 1. Setup mock result
    mock_node = TopologyNode(
        uid="aws::us-east-1::ec2::i-123",
        provider="aws",
        service="EC2",
        resource_type="compute/instance",
        category="compute",
        name="test-instance",
        region="us-east-1",
        account_id="123456789012"
    )
    
    mock_scan = TopologyScan(
        scan_id="test-scan",
        provider="aws",
        account_id="123456789012",
        regions_scanned=["us-east-1"],
        scanned_at="2024-01-01T00:00:00Z",
        nodes=[mock_node],
        edges=[]
    )
    
    # 2. Patch AWSDetector.discover
    with patch("apps.api.ingestors.pipeline.ingestors.AWSDetector") as MockDetector:
        instance = MockDetector.return_value
        instance.discover = MagicMock(return_value=asyncio.Future())
        instance.discover.return_value.set_result(mock_scan.to_discovery_result())
        
        # 3. Initialize Ingestor
        ingestor = AWSIngestor(region_name="us-east-1", credentials={"aws_access_key_id": "test"})
        
        # 4. Run Ingestion
        results = await ingestor.ingest()
        
        # 5. Verify
        assert len(results) == 1
        result = results[0]
        assert len(result.nodes) == 1
        assert result.nodes[0].key == "aws::us-east-1::ec2::i-123"
        assert result.metadata["regions_scanned"] == ["us-east-1"]

@pytest.mark.anyio
async def test_aws_ingestor_failure():
    # 1. Patch AWSDetector.discover to raise exception
    with patch("apps.api.ingestors.pipeline.ingestors.AWSDetector") as MockDetector:
        instance = MockDetector.return_value
        instance.discover = MagicMock(side_effect=Exception("AWS Error"))
        
        # 2. Initialize Ingestor
        ingestor = AWSIngestor(region_name="us-east-1", credentials={"aws_access_key_id": "test"})
        
        # 3. Run Ingestion
        results = await ingestor.ingest()
        
        # 4. Verify (should return empty list on failure)
        assert results == []
