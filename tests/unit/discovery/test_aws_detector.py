"""
Quick local test for AWSDetector — runs discovery against real AWS.

Usage (from repo root):
    source apps/api/venv/bin/activate
    python3 -m apps.api.test_aws_detector

Uses your default AWS credentials (from `aws configure` or env vars).
Pass --role-arn to test cross-account STS AssumeRole flow.
"""

import asyncio
import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from apps.api.ingestors.aws.detector import AWSDetector


async def run(region: str, credentials: dict, services: list[str] | None):
    detector = AWSDetector(region_name=region, credentials=credentials)

    if services:
        # Run only specific service discovery methods for a quick test
        from apps.api.ingestors.aws.schemas import DiscoveryNode
        nodes = []
        for svc in services:
            method_name = f"_discover_{svc}"
            method = getattr(detector, method_name, None)
            if not method:
                print(f"❌ No method {method_name} — available services:")
                available = [m.replace("_discover_", "") for m in dir(detector) if m.startswith("_discover_")]
                for a in sorted(available):
                    print(f"   • {a}")
                return
            print(f"\n🔍 Running {method_name}()...")
            result = method()
            nodes.extend(result)

        print(f"\n{'='*60}")
        print(f"✅ Discovered {len(nodes)} nodes from: {', '.join(services)}")
        for node in nodes:
            print(f"  [{node.node_type:12s}]  {node.key}")
            if node.properties:
                # Show first few properties
                for k, v in list(node.properties.items())[:5]:
                    val = str(v)[:80]
                    print(f"                   {k}: {val}")
    else:
        # Full discovery
        print("\n🔍 Running full discovery (all services)...")
        result = await detector.discover(include_relationships=True)

        print(f"\n{'='*60}")
        print(f"✅ Full Discovery Complete")
        print(f"   Nodes: {len(result.nodes)}")
        print(f"   Edges: {len(result.edges)}")
        print(f"   Region: {result.metadata.get('region')}")
        print(f"   Account: {result.metadata.get('account_id')}")

        # Group by type
        by_type: dict[str, list] = {}
        for n in result.nodes:
            by_type.setdefault(n.node_type, []).append(n)

        print(f"\n   Breakdown:")
        for ntype, items in sorted(by_type.items()):
            print(f"     {ntype:20s}  {len(items):3d} resources")
            for item in items[:3]:
                print(f"       → {item.key}")
            if len(items) > 3:
                print(f"       ... +{len(items)-3} more")

        if result.edges:
            print(f"\n   Sample edges:")
            for edge in result.edges[:10]:
                print(f"     {edge.from_node_key}  --[{edge.edge_type}]-->  {edge.to_node_key}")


def main():
    parser = argparse.ArgumentParser(description="Test AWSDetector locally")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--role-arn", default=None, help="IAM Role ARN for cross-account STS AssumeRole")
    parser.add_argument("--external-id", default=None, help="External ID for role assumption")
    parser.add_argument("--access-key", default=None, help="AWS Access Key ID (uses aws configure default if omitted)")
    parser.add_argument("--secret-key", default=None, help="AWS Secret Access Key")
    parser.add_argument("--services", nargs="+", default=None,
                        help="Specific services to test, e.g. --services ec2 s3 lambda. Omit for full discovery.")
    args = parser.parse_args()

    credentials = {"region": args.region}
    if args.access_key:
        credentials["aws_access_key_id"] = args.access_key
        credentials["aws_secret_access_key"] = args.secret_key
    if args.role_arn:
        credentials["role_arn"] = args.role_arn
    if args.external_id:
        credentials["external_id"] = args.external_id

    print(f"🧪 AWS Detector Test")
    print(f"   Region: {args.region}")
    print(f"   Role ARN: {args.role_arn or '(none — using default creds)'}")
    print(f"   Services: {', '.join(args.services) if args.services else 'ALL'}")

    asyncio.run(run(args.region, credentials, args.services))


if __name__ == "__main__":
    main()
