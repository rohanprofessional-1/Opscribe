from .base import BaseStage, ProcessingContext, IRNode, ValidationWarning

class NormalizeStage(BaseStage):
    def run(self, context: ProcessingContext) -> ProcessingContext:
        # AWS Normalization
        if context.raw_aws and "sources" in context.raw_aws:
            for source in context.raw_aws["sources"]:
                for node in source.get("nodes", []):
                    self._normalize_aws(node, context)

        # GitHub Normalization
        if context.raw_github and "sources" in context.raw_github:
            for source in context.raw_github["sources"]:
                for node in source.get("nodes", []):
                    self._normalize_github(node, context)
        
        return context

    def _normalize_aws(self, raw_node, context):
        props = raw_node.get("properties", {})
        key = raw_node["key"]
        
        service = props.get("service")
        if not service:
            # Fallback: extract from key if it follows the aws::{region}::{service}::{id} format
            key_parts = key.split("::")
            if len(key_parts) >= 3:
                service = key_parts[2]
        service = (service or "").upper()

        res_type = (props.get("resource_type") or raw_node.get("node_subtype") or "").lower()
        
        template_id = "unknown"
        node_type = "unknown"
        parent_group = None
        
        if service == "S3":
            template_id = "object-storage"
            node_type = "storage"
        elif service == "VPC":
            template_id = "vpc" # Changed from vpc-group
            node_type = "networking"
        elif service == "IAM":
            role_name = props.get("role_name", "")
            if role_name.startswith("AWSServiceRoleFor"):
                template_id = "iam" # Changed from iam-group
                node_type = "security"
                # Keep original key to avoid breaking raw edges, 
                # or handle merge in Resolve
            else:
                template_id = "iam"
                node_type = "security"
        elif service == "EC2":
            template_id = "vm"
            node_type = "compute"
        elif service == "RDS":
            template_id = "sql-db"
            node_type = "database"

        ir_node = IRNode(
            id=key,
            template_id=template_id,
            display_name=raw_node.get("display_name", key),
            node_type=node_type,
            source="aws",
            confidence=1.0,
            source_completeness="full",
            source_metadata=[{"source": "aws", "raw_key": raw_node["key"]}],
            properties=props,
            environment="aws-prod" # Default for now, could be inferred from account/region
        )

        if template_id == "unknown":
            ir_node.validation_warnings.append(ValidationWarning(
                type="unmapped_node",
                message=f"No template found for AWS service {service}",
                severity="info"
            ))

        # Handle iam-group merging early in normalize or in resolve? 
        # For singleton groups, we can merge here.
        if key in context.nodes and template_id == "iam-group":
            context.nodes[key].source_metadata.append(ir_node.source_metadata[0])
        else:
            context.nodes[key] = ir_node

    def _normalize_github(self, raw_node, context):
        props = raw_node.get("properties", {})
        image = props.get("image", "").lower()
        package = props.get("package", "").lower()
        key = raw_node["key"]
        
        template_id = "unknown"
        node_type = "unknown"
        
        if image:
            if "pgvector" in image or "postgres" in image:
                template_id = "sql-db"
                node_type = "database"
            elif "pgadmin" in image:
                template_id = "container"
                node_type = "compute"
            elif "minio" in image:
                template_id = "object-storage"
                node_type = "storage"
            else:
                template_id = "container"
                node_type = "compute"
        elif package:
            template_id = "dependency"
            node_type = "dependency"
            
        ir_node = IRNode(
            id=key,
            template_id=template_id,
            display_name=raw_node.get("display_name", key),
            node_type=node_type,
            source="github",
            confidence=0.9,
            source_completeness="full",
            source_metadata=[{"source": "github", "raw_key": raw_node["key"]}],
            properties=props,
            environment="local-dev" # Default for GitHub source
        )

        if template_id == "unknown":
            ir_node.validation_warnings.append(ValidationWarning(
                type="unmapped_node",
                message="No template found for GitHub resource",
                severity="info"
            ))

        context.nodes[key] = ir_node
