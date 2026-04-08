import json
import os
import sys
from uuid import UUID
from sqlmodel import Session, select

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from apps.api.database import engine
from apps.api.models import Client, Graph, Node, Edge
from apps.api.infrastructure.intermediate import ingest_to_graph
from apps.api.ingestors.aws.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge

AWS_FILE = "/Users/hardikk/Desktop/04-06-2026-22-42-28_files_list/aws.json"
GITHUB_FILE = "/Users/hardikk/Desktop/04-06-2026-22-42-28_files_list/github.json"

async def main():
    with Session(engine) as session:
        client = session.exec(select(Client)).first()
        if not client:
            print("No client found in database!")
            return
        
        print(f"Targeting client: {client.id} ({client.name})")
        
        results = []
        
        # Load AWS
        if os.path.exists(AWS_FILE):
            print(f"Loading AWS data from {AWS_FILE}")
            with open(AWS_FILE, "r") as f:
                payload = json.load(f)
                for source_data in payload.get("sources", []):
                    nodes = [DiscoveryNode(**n) for n in source_data.get("nodes", [])]
                    edges = [DiscoveryEdge(**e) for e in source_data.get("edges", [])]
                    results.append(DiscoveryResult(source=source_data.get("source", "aws"), nodes=nodes, edges=edges, metadata=source_data.get("metadata", {})))
        
        # Load GitHub
        if os.path.exists(GITHUB_FILE):
            print(f"Loading GitHub data from {GITHUB_FILE}")
            with open(GITHUB_FILE, "r") as f:
                payload = json.load(f)
                for source_data in payload.get("sources", []):
                    nodes = [DiscoveryNode(**n) for n in source_data.get("nodes", [])]
                    edges = [DiscoveryEdge(**e) for e in source_data.get("edges", [])]
                    results.append(DiscoveryResult(source=source_data.get("source", "github"), nodes=nodes, edges=edges, metadata=source_data.get("metadata", {})))

        if not results:
            print("No data found to ingest!")
            return

        print(f"Starting ingestion of {len(results)} source results...")
        await ingest_to_graph(client_id=client.id, results=results, session=session)
        print("✅ Ingestion complete!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
