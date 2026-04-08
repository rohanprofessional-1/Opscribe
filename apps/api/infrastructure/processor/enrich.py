from .base import BaseStage, ProcessingContext, IRNode, IREdge, ValidationWarning

class EnrichStage(BaseStage):
    def run(self, context: ProcessingContext) -> ProcessingContext:
        # 1. Ghost nodes for directories (representing inferred services)
        self._generate_ghost_nodes(context)
        
        # 2. Inferred edges (GitHub -> AWS)
        self._generate_inferred_edges(context)
        
        # 3. Handle resource containment (e.g. RDS inside VPC)
        self._handle_containment(context)

        # 4. Bake UI metadata (labels, icons, categories) for frontend compatibility
        self._apply_ui_metadata(context)
        
        return context

    def _generate_ghost_nodes(self, context):
        """
        Infer api-service based on directory paths.
        """
        found_dirs = set()
        if context.raw_github and "sources" in context.raw_github:
            for source in context.raw_github["sources"]:
                for node in source.get("nodes", []):
                    # Check requirements.txt or package.json
                    source_loc = node.get("properties", {}).get("related_files", [""])[0]
                    if not source_loc:
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
                    environment="both", # Spans between GitHub and AWS
                    validation_warnings=[ValidationWarning(
                        type="inferred_node",
                        message=f"Inferred service from directory: {dir_name}",
                        severity="info"
                    )]
                )

    def _generate_inferred_edges(self, context):
        """
        Infer relationships between GitHub services and AWS resources.
        """
        github_services = [
            n for n in context.nodes.values() 
            if n.source == "github" and n.node_type == "compute" or n.template_id == "api-service"
        ]
        
        aws_resources = [
            n for n in context.nodes.values() 
            if n.source == "aws" and n.node_type in ["storage", "database", "compute"]
        ]
        
        if not github_services or not aws_resources:
            return

        for github_node in github_services:
            for aws_node in aws_resources:
                if github_node.id == aws_node.id:
                    continue
                
                edge_type = "accesses"
                if aws_node.template_id == "sql-db":
                    edge_type = "connects_to"
                
                context.edges.append(IREdge(
                    id=f"inferred-cross-provider-{len(context.edges)}",
                    from_node_id=github_node.id,
                    to_node_id=aws_node.id,
                    edge_type=edge_type,
                    source="inferred",
                    confidence=0.7,
                    environment="both",
                    properties={"inference_rule": "cross_provider_dependency"}
                ))

    def _apply_ui_metadata(self, context: ProcessingContext):
        """
        Maps backend template_ids and types to frontend mandatory fields.
        Ensures nodes show up in the UI with correct icons, colors, and labels.
        """
        # Mapping from template_id to Lucide icon name (matching nodeTemplates.ts)
        ICON_MAP = {
            "sql-db": "Database",
            "nosql-db": "Layers",
            "object-storage": "Archive",
            "vm": "Server",
            "container": "Box",
            "serverless": "Cloud",
            "vpc": "Network",
            "iam": "Users",
            "api-service": "Cpu",
            "dependency": "Package",
            "networking-group": "Globe",
            "iam-group": "Lock",
            "unknown": "HelpCircle"
        }

        for node in context.nodes.values():
            # 1. Label
            node.properties["label"] = node.display_name or node.id
            
            # 2. Category (must match frontend NodeCategory union)
            # database, compute, storage, networking, security, messaging
            cat = node.node_type
            if cat not in ["database", "compute", "storage", "networking", "security", "messaging"]:
                cat = "compute" # Default fallback
            node.properties["category"] = cat
            
            # 3. Icon
            node.properties["icon"] = ICON_MAP.get(node.template_id, ICON_MAP["unknown"])

    def _handle_containment(self, context):
        """
        Assign AWS resources to their containing VPCs if available.
        """
        vpc_nodes = [n for n in context.nodes.values() if n.template_id == "vpc"]
        if not vpc_nodes:
            return
            
        for node in context.nodes.values():
            if node.source == "aws" and node.template_id != "vpc":
                if node.template_id in ["vm", "sql-db", "serverless", "container", "security-group"]:
                    node.parent_id = vpc_nodes[0].id
                    context.edges.append(IREdge(
                        id=f"membership-{node.id}",
                        from_node_id=vpc_nodes[0].id,
                        to_node_id=node.id,
                        edge_type="contains",
                        source="inferred",
                        confidence=1.0,
                        environment=node.environment
                    ))
