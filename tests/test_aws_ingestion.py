import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from dotenv import dotenv_values

# Add project root to sys.path
sys.path.append(os.getcwd())

from apps.api.ingestors.pipeline.ingestors import AWSIngestor

async def run_manual_ingestion(region="us-east-1"):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # 1. Load credentials from .env
    env_path = "apps/api/.env"
    if not os.path.exists(env_path):
        logger.error(f"Could not find {env_path}")
        return

    env = dotenv_values(env_path)
    credentials = {
        "aws_access_key_id": env.get("OPSCRIBE_AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": env.get("OPSCRIBE_AWS_SECRET_ACCESS_KEY"),
        # Use a role_arn if configured in the environment
        "role_arn": env.get("OPSCRIBE_AWS_ROLE_ARN"),
    }

    if not credentials["aws_access_key_id"]:
        logger.error("AWS credentials not found in .env")
        return

    # 2. Initialize Ingestor
    logger.info(f"Starting AWS ingestion (Region: {region})...")
    ingestor = AWSIngestor(region_name=region, credentials=credentials)

    # 3. Run Ingestion
    results = await ingestor.ingest()
    if not results:
        logger.error("Ingestion returned no results.")
        return

    # 4. Process Results (Aggregation)
    # The ingestor returns a list of DiscoveryResult objects.
    # We combine them for the final output.
    final_output = {
        "nodes": [],
        "edges": [],
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "source": "aws",
            "regions_scanned": [],
        }
    }

    for res in results:
        final_output["nodes"].extend([node.dict() for node in res.nodes])
        final_output["edges"].extend([edge.dict() for edge in res.edges])
        if "regions_scanned" in res.metadata:
            final_output["metadata"]["regions_scanned"].extend(res.metadata["regions_scanned"])

    # Unique regions
    final_output["metadata"]["regions_scanned"] = list(set(final_output["metadata"]["regions_scanned"]))
    
    # 5. Save to local file
    output_dir = "tests/output"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"aws_discovery_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        json.dump(final_output, f, indent=2, default=str)

    logger.info("=" * 40)
    logger.info(f"INGESTION COMPLETE")
    logger.info(f"Nodes found: {len(final_output['nodes'])}")
    logger.info(f"Edges found: {len(final_output['edges'])}")
    logger.info(f"Regions: {final_output['metadata']['regions_scanned']}")
    logger.info(f"JSON saved to: {filepath}")
    logger.info("=" * 40)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manual AWS Ingestion Debug Tool")
    parser.add_argument("--region", default="us-east-1", help="Bootstrap region (default: us-east-1)")
    args = parser.parse_args()
    
    asyncio.run(run_manual_ingestion(args.region))
