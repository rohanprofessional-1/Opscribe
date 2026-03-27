from .base import BaseStage, ProcessingContext, ValidationWarning

class ValidateStage(BaseStage):
    def run(self, context: ProcessingContext) -> ProcessingContext:
        # 1. Partial Scan Warning (AWS 0 edges)
        # Assuming we check raw_aws for edges before internal state
        aws_edges = []
        if context.raw_aws and "sources" in context.raw_aws:
            for source in context.raw_aws["sources"]:
                aws_edges.extend(source.get("edges", []))
        
        if not aws_edges:
            context.graph_metadata["source_completeness"] = "partial"
            context.graph_metadata["warnings"].append(ValidationWarning(
                type="partial_scan",
                message="AWS export returns zero edges; data may be incomplete",
                severity="warn"
            ))
            # Attach to all AWS nodes
            for node in context.nodes.values():
                if node.source == "aws":
                    node.source_completeness = "partial"
                    node.validation_warnings.append(ValidationWarning(
                        type="partial_scan",
                        message="Potential partial scan",
                        severity="warn"
                    ))

        # 2. Empty Container Warning
        containers = [n for n in context.nodes.values() if n.node_type == "group" or n.template_id == "vpc-group"]
        for container in containers:
            children = [n for n in context.nodes.values() if n.parent_id == container.id]
            if not children:
                container.validation_warnings.append(ValidationWarning(
                    type="empty_container",
                    message="Container has no child resources",
                    severity="warn"
                ))

        # 3. Cross-Environment Edge Warning
        for edge in context.edges:
            from_node = context.nodes.get(edge.from_node_id)
            to_node = context.nodes.get(edge.to_node_id)
            if from_node and to_node:
                if from_node.environment != "both" and to_node.environment != "both" and from_node.environment != to_node.environment:
                    from_node.validation_warnings.append(ValidationWarning(
                        type="cross_environment_edge",
                        message=f"Resource links to {to_node.environment} resource: {to_node.id}",
                        severity="warn"
                    ))

        return context
