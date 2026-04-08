from .base import BaseStage, ProcessingContext, IRNode, IREdge

class ResolveStage(BaseStage):
    def run(self, context: ProcessingContext) -> ProcessingContext:
        nodes_to_remove = []
        
        # 1. Capture original edges from sources
        if context.raw_github and "sources" in context.raw_github:
            for source in context.raw_github["sources"]:
                for edge in source.get("edges", []):
                    context.edges.append(IREdge(
                        id=f"github-edge-{len(context.edges)}",
                        from_node_id=edge["from_node_key"],
                        to_node_id=edge["to_node_key"],
                        edge_type=edge.get("edge_type", "depends_on"),
                        source="github",
                        confidence=0.9,
                        environment="local-dev"
                    ))

        # 2. Capture original edges from AWS sources
        if context.raw_aws and "sources" in context.raw_aws:
            for source in context.raw_aws["sources"]:
                for edge in source.get("edges", []):
                    context.edges.append(IREdge(
                        id=f"aws-edge-{len(context.edges)}",
                        from_node_id=edge["from_node_key"],
                        to_node_id=edge["to_node_key"],
                        edge_type=edge.get("edge_type", "references"),
                        source="aws",
                        confidence=1.0,
                        environment="aws-prod",
                        properties=edge.get("properties", {})
                    ))

        # 2. Process Nodes for merging/suppression
        for key, node in list(context.nodes.items()):
            props = node.properties
            package = props.get("package", "").lower()
            
            # VPC Association for AWS nodes
            if node.source == "aws" and node.template_id != "vpc-group":
                # In many cases, VPC ID is in the ARN or a specific property
                # For now, we'll try to find a VPC node and assign parent if possible
                # (Actual VPC membership logic would depend on subnets/etc, 
                # but for IR we can use heuristics if needed)
                pass

            # Dependency Suppression
            if package:
                # Find canonical node by service name or type
                # e.g. "pgvector" -> "sql-db"
                # e.g. "boto3" -> "object-storage"
                target_node = None
                if "pgvector" in package or "postgres" in package:
                    target_node = next((n for n in context.nodes.values() if n.template_id == "sql-db"), None)
                elif "minio" in package:
                    target_node = next((n for n in context.nodes.values() if n.template_id == "object-storage"), None)
                
                if target_node:
                    # Redirect any edges pointing to this package/dependency to the canonical service node
                    self._redirect_edges(context, key, target_node.id)
                    target_node.source_metadata.append(node.source_metadata[0])
                
                # Always remove the raw dependency node after redirection attempt
                nodes_to_remove.append(key)

        for key in nodes_to_remove:
            if key in context.nodes:
                del context.nodes[key]

        return context

    def _redirect_edges(self, context, old_id, new_id):
        for edge in context.edges:
            if edge.from_node_id == old_id:
                edge.from_node_id = new_id
            if edge.to_node_id == old_id:
                edge.to_node_id = new_id
