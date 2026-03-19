#!/usr/bin/env python3
"""
Quick Start Script - Easiest way to test AWS detection

Run this to get started immediately!
"""

import asyncio
import sys
import os

# Add the apps/api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps/api'))

from apps.api.ingestors.aws.detector import AWSDetector


async def main():
    print("\n" + "="*60)
    print("AWS SERVICE DETECTION - QUICK START")
    print("="*60 + "\n")
    
    # Step 1: Check credentials
    print("Step 1: Checking AWS credentials...")
    try:
        detector = AWSDetector(region_name="us-east-1")
        account_id = detector._get_account_id()
        print(f"✓ Connected to AWS Account: {account_id}")
        print(f"✓ Region: us-east-1\n")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nPlease configure AWS credentials first!")
        print("See TESTING_AWS_DETECTION.md for setup instructions.\n")
        return
    
    # Step 2: Run discovery
    print("Step 2: Discovering AWS resources...")
    print("(This may take 30-60 seconds...\n")
    
    try:
        result = await detector.discover()
    except Exception as e:
        print(f"✗ Discovery failed: {e}\n")
        return
    
    # Step 3: Display results
    print("\n" + "="*60)
    print("DISCOVERY RESULTS")
    print("="*60 + "\n")
    
    print(f"✓ Found {len(result.nodes)} total resources")
    print(f"✓ Detected {len(result.edges)} relationships\n")
    
    # Group by service
    by_service = {}
    for node in result.nodes:
        service = node.properties.get("service", "Unknown")
        if service not in by_service:
            by_service[service] = []
        by_service[service].append(node)
    
    # Show summary
    print("Summary by Service Category:\n")
    
    services_shown = 0
    for service in sorted(by_service.keys()):
        nodes = by_service[service]
        print(f"{service} ({len(nodes)} resources):")
        
        # Show first 3 resources from each service
        for node in nodes[:3]:
            print(f"  • {node.display_name}")
        
        if len(nodes) > 3:
            print(f"  ... and {len(nodes) - 3} more")
        
        print()
        services_shown += 1
        
        if services_shown >= 5:
            remaining = len(by_service) - services_shown
            if remaining > 0:
                print(f"... and {remaining} more service types")
            break
    
    # Show relationships
    if result.edges:
        print(f"\nRelationships detected:")
        by_edge_type = {}
        for edge in result.edges:
            edge_type = edge.edge_type
            by_edge_type[edge_type] = by_edge_type.get(edge_type, 0) + 1
        
        for edge_type, count in sorted(by_edge_type.items()):
            print(f"  • {edge_type}: {count}")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60 + "\n")
    
    print("1. Read TESTING_AWS_DETECTION.md for detailed testing examples")
    print("2. Run the interactive tester:")
    print("   python3 apps/api/test_interactive.py")
    print("3. Test individual services (see README for examples)")
    print("4. Modify the detector to add more service detections")
    print("5. Integrate with the API endpoints")
    print("\nHappy learning! 🚀\n")


if __name__ == "__main__":
    asyncio.run(main())
