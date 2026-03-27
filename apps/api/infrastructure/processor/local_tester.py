import json
import os
import sys
from dataclasses import asdict

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlmodel import Session, select, text
from apps.api.database import engine
from apps.api.models import Node, Edge, NodeType, EdgeType, Graph
from apps.api.infrastructure.processor.pipeline import InfrastructurePipeline

GITHUB_FILE = "/Users/hardikk/Desktop/github_latest.json"
AWS_FILE = "/Users/hardikk/Desktop/aws_latest.json"
CLIENT_ID = "123e4567-e89b-12d3-a456-426614174000"
GRAPH_ID = "0a1f13b0-aa75-44e2-82f5-dc418872a265"

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def run_modular_ingest():
    github_data = load_json(GITHUB_FILE)
    aws_data = load_json(AWS_FILE)

    # 1. Execute Pipeline
    pipeline = InfrastructurePipeline()
    context = pipeline.execute(github_data, aws_data)

    print(f"Pipeline complete: {len(context.nodes)} nodes, {len(context.edges)} edges.")

    # 2. Serialize and Save to JSON
    output_dir = "/Users/hardikk/Desktop/Opscribe/apps/api/infrastructure/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "infrastructure_ir.json")

    ir_data = {
        "nodes": [],
        "edges": []
    }

    for ir_node in context.nodes.values():
        node_dict = {
            "id": ir_node.id,
            "template_id": ir_node.template_id,
            "display_name": ir_node.display_name,
            "node_type": ir_node.node_type,
            "parent_id": ir_node.parent_id,
            "environment": ir_node.environment,
            "source": ir_node.source,
            "confidence": ir_node.confidence,
            "source_completeness": ir_node.source_completeness,
            "source_metadata": ir_node.source_metadata,
            "properties": ir_node.properties,
            "validation_warnings": [asdict(w) for w in ir_node.validation_warnings]
        }
        ir_data["nodes"].append(node_dict)

    for ir_edge in context.edges:
        edge_dict = {
            "id": ir_edge.id,
            "from_node_id": ir_edge.from_node_id,
            "to_node_id": ir_edge.to_node_id,
            "edge_type": ir_edge.edge_type,
            "source": ir_edge.source,
            "confidence": ir_edge.confidence,
            "environment": ir_edge.environment,
            "properties": ir_edge.properties
        }
        ir_data["edges"].append(edge_dict)

    with open(output_path, "w") as f:
        json.dump(ir_data, f, indent=2)

    print(f"Modular IR saved to: {output_path}")

if __name__ == "__main__":
    run_modular_ingest()
