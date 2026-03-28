from .base import BaseStage, ProcessingContext, IRNode, IREdge, ValidationWarning

class EnrichStage(BaseStage):
    def run(self, context: ProcessingContext) -> ProcessingContext:
        # 1. Ghost nodes for directories
        self._generate_ghost_nodes(context)
        
        # 2. Inferred edges (boto3 -> S3)
        self._generate_inferred_edges(context)
        
        # 3. Container groups
        self._generate_container_groups(context)
        
        return context

    def _generate_ghost_nodes(self, context):
        """
        Infer api-service based on directory paths.
        """
        # Look at raw nodes that were dependencies
        found_dirs = set()
        if context.raw_github and "sources" in context.raw_github:
            for source in context.raw_github["sources"]:
                for node in source.get("nodes", []):
                    # Check requirements.txt or package.json
                    source_loc = node.get("properties", {}).get("source_location", "")
                    if "api" in source_loc or "requirements.txt" in source_loc:
                        dir_name = source_loc.split("/")[0] if "/" in source_loc else "root"
                        found_dirs.add(dir_name)
        
        for dir_name in found_dirs:
            key = f"github:service:{dir_name}"
            if key not in context.nodes:
                context.nodes[key] = IRNode(
                    id=key,
                    template_id="api-service",
                    display_name=f"{dir_name}-service",
                    node_type="compute",
                    source="inferred",
                    confidence=0.6,
                    source_completeness="inferred",
                    validation_warnings=[ValidationWarning(
                        type="inferred_node",
                        message=f"Inferred service from directory: {dir_name}",
                        severity="info"
                    )]
                )

    def _generate_inferred_edges(self, context):
        """
        SDK dependency (boto3) -> S3 accesses edge.
        """
        # We need to find the inferred api service to associate it with the SDK requirement
        api_service = next((n for n in context.nodes.values() if n.template_id == "api-service"), None)
        s3_buckets = [n for n in context.nodes.values() if n.template_id == "object-storage" and n.source == "aws"]
        
        if api_service:
            for s3 in s3_buckets:
                context.edges.append(IREdge(
                    id=f"inferred-edge-{len(context.edges)}",
                    from_node_id=api_service.id,
                    to_node_id=s3.id,
                    edge_type="accesses",
                    source="inferred",
                    confidence=0.8,
                    environment="both"
                ))

    def _generate_container_groups(self, context):
        # 1. env-group nodes
        env_dev = IRNode(
            id="group:env:dev",
            template_id="env-group",
            display_name="dev-environment",
            node_type="group",
            environment="dev",
            source="inferred"
        )
        env_prod = IRNode(
            id="group:env:prod",
            template_id="env-group",
            display_name="prod-environment",
            node_type="group",
            environment="prod",
            source="inferred"
        )
        context.nodes[env_dev.id] = env_dev
        context.nodes[env_prod.id] = env_prod
        
        # 2. vpc-group nodes (Now using canonical 'vpc' ID)
        vpc_nodes = [n for n in context.nodes.values() if n.template_id == "vpc"]
        for vpc in vpc_nodes:
            vpc.parent_id = env_prod.id
            context.edges.append(IREdge(
                id=f"membership-vpc-{vpc.id}",
                from_node_id=env_prod.id,
                to_node_id=vpc.id,
                edge_type="contains",
                source="inferred",
                confidence=1.0,
                environment="prod",
                properties={"reason": "vpc_in_prod_env"}
            ))
        
        # 3. Associate nodes with parents
        for node in context.nodes.values():
            if node.id in ["group:env:dev", "group:env:prod"]:
                continue
            
            if node.source == "github":
                node.parent_id = env_dev.id
            elif node.source == "aws":
                if node.template_id == "vpc": # Changed from vpc-group
                    node.parent_id = env_prod.id
                else:
                    # By specifications, inside-vpc nodes get vpc group as parent
                    # We'll assign to the first vpc group for now (as a simplified mapping)
                    if vpc_nodes and node.node_type in ["compute", "database", "networking", "storage"]:
                        # Heuristic: S3 is account-level, RDS is inside-vpc
                        if node.template_id in ["vm", "sql-db", "serverless", "container"]:
                            node.parent_id = vpc_nodes[0].id
                            context.edges.append(IREdge(
                                id=f"membership-rds-{node.id}",
                                from_node_id=vpc_nodes[0].id,
                                to_node_id=node.id,
                                edge_type="contains",
                                source="inferred",
                                confidence=1.0,
                                environment="prod"
                            ))
                        else:
                            node.parent_id = env_prod.id
                            context.edges.append(IREdge(
                                id=f"membership-res-{node.id}",
                                from_node_id=env_prod.id,
                                to_node_id=node.id,
                                edge_type="contains",
                                source="inferred",
                                confidence=1.0,
                                environment="prod"
                            ))
                    else:
                        node.parent_id = env_prod.id
                        context.edges.append(IREdge(
                            id=f"membership-env-{node.id}",
                            from_node_id=env_prod.id,
                            to_node_id=node.id,
                            edge_type="contains",
                            source="inferred",
                            confidence=1.0,
                            environment="prod"
                        ))
