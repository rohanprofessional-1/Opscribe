import boto3
import logging
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError, BotoCoreError
from apps.api.ingestors.aws.base import BaseDetector
from apps.api.ingestors.aws.schemas import DiscoveryResult, DiscoveryNode, DiscoveryEdge

logger = logging.getLogger(__name__)


class AWSServiceDetector:
    """Base class for AWS service-specific detection logic"""

    def __init__(self, boto_client):
        self.client = boto_client

    def _get_name_tag(self, tags: List[Dict]) -> Optional[str]:
        """Extract Name tag from resource tags"""
        if not tags:
            return None
        for tag in tags:
            if tag.get("Key") == "Name" or tag.get("key") == "Name":
                return tag.get("Value")
        return None


import os
from dotenv import dotenv_values

class AWSDetector(BaseDetector):
    """Comprehensive AWS infrastructure detector covering all major services"""

    def __init__(self, region_name: str = "us-east-1", credentials: dict = None):
        self.region_name = region_name
        self.credentials = credentials or {}
        self.account_id = None
        self._temp_credentials = None

    def _get_client(self, service_name: str):
        """Centralized factory for boto3 clients using DB credentials, STS AssumeRole, or .env fallback."""
        env = dotenv_values("apps/api/.env")
        
        # Base credentials (must be tenant-provided)
        access_key = self.credentials.get("aws_access_key_id")
        secret_key = self.credentials.get("aws_secret_access_key")
        session_token = self.credentials.get("aws_session_token")
        
        # Cross-Account Role Assumption (Enterprise Standard)
        role_arn = self.credentials.get("role_arn")
        if role_arn:
            if not self._temp_credentials:
                # Use Opscribe's global AWS credentials ONLY to broker the STS AssumeRole call.
                # We prioritize OPSCRIBE_AWS_ prefixed keys if set in .env to avoid collision with mocks.
                sts_access = env.get("OPSCRIBE_AWS_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID")
                sts_secret = env.get("OPSCRIBE_AWS_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
                
                sts_kwargs = {
                    "service_name": "sts",
                    "region_name": self.region_name
                }
                if sts_access:
                    sts_kwargs["aws_access_key_id"] = sts_access
                    sts_kwargs["aws_secret_access_key"] = sts_secret
                    
                sts = boto3.client(**sts_kwargs)
                
                assume_role_kwargs = {
                    "RoleArn": role_arn,
                    "RoleSessionName": f"OpscribeDiscovery-{self.account_id or 'Init'}"
                }
                
                # External ID for Confused Deputy protection
                external_id = self.credentials.get("external_id")
                if external_id:
                    assume_role_kwargs["ExternalId"] = external_id
                    
                logger.info(f"Assuming role {role_arn} for discovery...")
                response = sts.assume_role(**assume_role_kwargs)
                self._temp_credentials = response['Credentials']
            
            # Downgrade to the temporary tenant credentials
            access_key = self._temp_credentials['AccessKeyId']
            secret_key = self._temp_credentials['SecretAccessKey']
            session_token = self._temp_credentials['SessionToken']
            
        endpoint_url = self.credentials.get("endpoint_url")
        region = self.credentials.get("region")
        
        client_kwargs = {
            "service_name": service_name,
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if session_token:
            client_kwargs["aws_session_token"] = session_token
        
        # S3 local endpoint support (e.g., MinIO)
        if service_name == "s3" and endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
            
        return boto3.client(**client_kwargs)

    @property
    def source_name(self) -> str:
        return "aws"

    def _get_name_tag(self, tags: List[Dict]) -> Optional[str]:
        """Extract Name tag from resource tags"""
        if not tags:
            return None
        for tag in tags:
            if tag.get("Key") == "Name" or tag.get("key") == "Name":
                return tag.get("Value")
        return None

    def _get_tags_dict(self, tags: List[Dict]) -> Dict[str, str]:
        """Convert AWS resource tags list to a dictionary"""
        if not tags:
            return {}
        return {tag.get("Key") or tag.get("key"): tag.get("Value") or tag.get("value") for tag in tags if tag.get("Key") or tag.get("key")}

    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        if not self.account_id:
            try:
                sts = self._get_client("sts")
                self.account_id = sts.get_caller_identity()["Account"]
            except Exception as e:
                logger.warning(f"Could not retrieve account ID: {e}")
                self.account_id = "000000000000"
        return self.account_id

    async def discover(self, include_relationships: bool = True, **kwargs) -> DiscoveryResult:
        nodes: List[DiscoveryNode] = []
        edges: List[DiscoveryEdge] = []

        try:
            # COMPUTE SERVICES
            logger.info("Discovering EC2 instances...")
            nodes.extend(self._discover_ec2())

            logger.info("Discovering Lambda functions...")
            nodes.extend(self._discover_lambda())

            logger.info("Discovering ECS clusters and services...")
            nodes.extend(self._discover_ecs())

            logger.info("Discovering EKS clusters...")
            nodes.extend(self._discover_eks())

            # STORAGE SERVICES
            logger.info("Discovering S3 buckets...")
            nodes.extend(self._discover_s3())

            logger.info("Discovering EBS volumes...")
            nodes.extend(self._discover_ebs())

            logger.info("Discovering EFS file systems...")
            nodes.extend(self._discover_efs())

            logger.info("Discovering FSx file systems...")
            nodes.extend(self._discover_fsx())

            # DATABASE SERVICES
            logger.info("Discovering RDS instances...")
            nodes.extend(self._discover_rds())

            logger.info("Discovering DynamoDB tables...")
            nodes.extend(self._discover_dynamodb())

            logger.info("Discovering Redshift clusters...")
            nodes.extend(self._discover_redshift())

            # NETWORKING/CDN
            logger.info("Discovering VPCs...")
            nodes.extend(self._discover_vpc())

            logger.info("Discovering Load Balancers...")
            nodes.extend(self._discover_load_balancers())

            logger.info("Discovering CloudFront distributions...")
            nodes.extend(self._discover_cloudfront())

            logger.info("Discovering Direct Connect...")
            nodes.extend(self._discover_direct_connect())

            # SECURITY/IAM
            logger.info("Discovering IAM roles...")
            nodes.extend(self._discover_iam_roles())

            logger.info("Discovering KMS keys...")
            nodes.extend(self._discover_kms())

            logger.info("Discovering Secrets Manager secrets...")
            nodes.extend(self._discover_secrets_manager())

            logger.info("Discovering Directory Service...")
            nodes.extend(self._discover_directory_service())

            # OBSERVABILITY/OPS
            logger.info("Discovering CloudWatch log groups...")
            nodes.extend(self._discover_cloudwatch())

            logger.info("Discovering CloudTrail trails...")
            nodes.extend(self._discover_cloudtrail())

            logger.info("Discovering Systems Manager...")
            nodes.extend(self._discover_systems_manager())

            # INTEGRATION
            logger.info("Discovering SQS queues...")
            nodes.extend(self._discover_sqs())

            logger.info("Discovering SNS topics...")
            nodes.extend(self._discover_sns())

            logger.info("Discovering EventBridge rules...")
            nodes.extend(self._discover_eventbridge())

            logger.info("Discovering API Gateway APIs...")
            nodes.extend(self._discover_api_gateway())

            # Detect relationships between resources
            if include_relationships:
                logger.info("Detecting resource relationships...")
                edges.extend(self._detect_relationships(nodes))
            else:
                logger.info("Skipping relationship detection for datalake population.")

        except Exception as e:
            logger.error(f"AWS discovery failed: {e}", exc_info=True)

        return DiscoveryResult(
            source=self.source_name,
            nodes=nodes,
            edges=edges,
            metadata={"region": self.region_name, "account_id": self._get_account_id()},
        )

    # ============= COMPUTE SERVICES =============

    def _discover_ec2(self) -> List[DiscoveryNode]:
        """Discover EC2 instances"""
        nodes = []
        try:
            ec2 = self._get_client("ec2")
            response = ec2.describe_instances()

            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    name = self._get_name_tag(instance.get("Tags", []))

                    nodes.append(
                        DiscoveryNode(
                            key=f"ec2:{instance_id}",
                            display_name=name or instance_id,
                            node_type="compute",
                            properties={
                                "service": "EC2",
                                "instance_id": instance_id,
                                "instance_type": instance["InstanceType"],
                                "state": instance["State"]["Name"],
                                "private_ip": instance.get("PrivateIpAddress"),
                                "public_ip": instance.get("PublicIpAddress"),
                                "availability_zone": instance.get("Placement", {}).get(
                                    "AvailabilityZone"
                                ),
                                "vpc_id": instance.get("VpcId"),
                                "subnet_id": instance.get("SubnetId"),
                                "security_groups": [
                                    sg["GroupId"]
                                    for sg in instance.get("SecurityGroups", [])
                                ],
                                "image_id": instance.get("ImageId"),
                                "iam_instance_profile": instance.get("IamInstanceProfile", {}).get("Arn"),
                                "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                                "monitoring": instance.get("Monitoring", {}).get("State"),
                                "public_dns_name": instance.get("PublicDnsName"),
                                "tags": self._get_tags_dict(instance.get("Tags", [])),
                            },
                            source_metadata={
                                "arn": f"arn:aws:ec2:{self.region_name}:{self._get_account_id()}:instance/{instance_id}"
                            },
                        )
                    )
        except ClientError as e:
            logger.warning(f"EC2 discovery error: {e}")

        return nodes

    def _discover_lambda(self) -> List[DiscoveryNode]:
        """Discover Lambda functions"""
        nodes = []
        try:
            lambda_client = self._get_client("lambda")
            paginator = lambda_client.get_paginator("list_functions")

            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    func_name = func["FunctionName"]
                    nodes.append(
                        DiscoveryNode(
                            key=f"lambda:{func_name}",
                            display_name=func_name,
                            node_type="compute",
                            properties={
                                "service": "Lambda",
                                "function_name": func_name,
                                "runtime": func.get("Runtime"),
                                "handler": func.get("Handler"),
                                "memory_size": func.get("MemorySize"),
                                "timeout": func.get("Timeout"),
                                "vpc_id": func.get("VpcConfig", {}).get("VpcId"),
                                "role_arn": func.get("Role"),
                                "description": func.get("Description"),
                                "last_modified": func.get("LastModified"),
                                "layers": [l.get("Arn") for l in func.get("Layers", [])],
                                "tags": self._get_tags_dict(func.get("Tags", [])), # list_functions doesn't return tags, usually need separate call
                            },
                            source_metadata={"arn": func["FunctionArn"]},
                        )
                    )
        except ClientError as e:
            logger.warning(f"Lambda discovery error: {e}")

        return nodes

    def _discover_ecs(self) -> List[DiscoveryNode]:
        """Discover ECS clusters and services"""
        nodes = []
        try:
            ecs = self._get_client("ecs")
            clusters = ecs.list_clusters().get("clusterArns", [])

            for cluster_arn in clusters:
                cluster_name = cluster_arn.split("/")[-1]
                nodes.append(
                    DiscoveryNode(
                        key=f"ecs:cluster:{cluster_name}",
                        display_name=cluster_name,
                        node_type="compute",
                        properties={
                            "service": "ECS",
                            "cluster_type": "cluster",
                            "cluster_name": cluster_name,
                        },
                        source_metadata={"arn": cluster_arn},
                    )
                )

                # Get services in this cluster
                services = ecs.list_services(cluster=cluster_arn).get("serviceArns", [])
                for service_arn in services:
                    service_name = service_arn.split("/")[-1]
                    nodes.append(
                        DiscoveryNode(
                            key=f"ecs:service:{cluster_name}:{service_name}",
                            display_name=f"{cluster_name}/{service_name}",
                            node_type="compute",
                            properties={
                                "service": "ECS",
                                "cluster_type": "service",
                                "cluster_name": cluster_name,
                                "service_name": service_name,
                            },
                            source_metadata={"arn": service_arn},
                        )
                    )
        except ClientError as e:
            logger.warning(f"ECS discovery error: {e}")

        return nodes

    def _discover_eks(self) -> List[DiscoveryNode]:
        """Discover EKS clusters"""
        nodes = []
        try:
            eks = self._get_client("eks")
            clusters = eks.list_clusters().get("clusters", [])

            for cluster_name in clusters:
                cluster = eks.describe_cluster(name=cluster_name).get("cluster", {})
                nodes.append(
                    DiscoveryNode(
                        key=f"eks:{cluster_name}",
                        display_name=cluster_name,
                        node_type="compute",
                        properties={
                            "service": "EKS",
                            "cluster_name": cluster_name,
                            "version": cluster.get("version"),
                            "status": cluster.get("status"),
                            "vpc_id": cluster.get("resourcesVpcConfig", {}).get(
                                "vpcId"
                            ),
                        },
                        source_metadata={"arn": cluster.get("arn")},
                    )
                )
        except ClientError as e:
            logger.warning(f"EKS discovery error: {e}")

        return nodes

    # ============= STORAGE SERVICES =============

    def _discover_s3(self) -> List[DiscoveryNode]:
        """Discover S3 buckets"""
        nodes = []
        try:
            s3 = self._get_client("s3")
            response = s3.list_buckets()

            for bucket in response.get("Buckets", []):
                bucket_name = bucket["Name"]
                tags = []

                # Try to fetch bucket tags
                try:
                    tags_response = s3.get_bucket_tagging(Bucket=bucket_name)
                    tag_list = tags_response.get("TagSet", [])
                    tags_dict = self._get_tags_dict(tag_list)
                except ClientError:
                    # Tags might not exist for some buckets
                    tags_dict = {}

                # Try to fetch bucket location
                try:
                    location_response = s3.get_bucket_location(Bucket=bucket_name)
                    location = location_response.get("LocationConstraint") or "us-east-1"
                except ClientError:
                    location = self.region_name

                nodes.append(
                    DiscoveryNode(
                        key=f"s3:{bucket_name}",
                        display_name=bucket_name,
                        node_type="storage",
                        properties={
                            "service": "S3",
                            "bucket_name": bucket_name,
                            "creation_date": (
                                bucket.get("CreationDate").isoformat()
                                if bucket.get("CreationDate")
                                else None
                            ),
                            "tags": tags_dict,
                            "location": location,
                        },
                        source_metadata={"arn": f"arn:aws:s3:::{bucket_name}"},
                    )
                )
        except ClientError as e:
            logger.warning(f"S3 discovery error: {e}")

        return nodes

    def _discover_ebs(self) -> List[DiscoveryNode]:
        """Discover EBS volumes"""
        nodes = []
        try:
            ec2 = self._get_client("ec2")
            response = ec2.describe_volumes()

            for volume in response.get("Volumes", []):
                volume_id = volume["VolumeId"]
                name = self._get_name_tag(volume.get("Tags", []))

                nodes.append(
                    DiscoveryNode(
                        key=f"ebs:{volume_id}",
                        display_name=name or volume_id,
                        node_type="storage",
                        properties={
                            "service": "EBS",
                            "volume_id": volume_id,
                            "size": volume["Size"],
                            "volume_type": volume["VolumeType"],
                            "state": volume["State"],
                            "availability_zone": volume["AvailabilityZone"],
                            "attached_to": [
                                att["InstanceId"]
                                for att in volume.get("Attachments", [])
                            ],
                        },
                        source_metadata={
                            "arn": f"arn:aws:ec2:{self.region_name}:{self._get_account_id()}:volume/{volume_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"EBS discovery error: {e}")

        return nodes

    def _discover_efs(self) -> List[DiscoveryNode]:
        """Discover EFS file systems"""
        nodes = []
        try:
            efs = self._get_client("efs")
            response = efs.describe_file_systems()

            for fs in response.get("FileSystems", []):
                fs_id = fs["FileSystemId"]
                name = fs.get("Name", fs_id)

                nodes.append(
                    DiscoveryNode(
                        key=f"efs:{fs_id}",
                        display_name=name,
                        node_type="storage",
                        properties={
                            "service": "EFS",
                            "file_system_id": fs_id,
                            "state": fs["LifeCycleState"],
                            "size_bytes": fs.get("SizeInBytes", {}).get("Value"),
                            "performance_mode": fs.get("PerformanceMode"),
                            "throughput_mode": fs.get("ThroughputMode"),
                        },
                        source_metadata={"arn": fs.get("FileSystemArn")},
                    )
                )
        except ClientError as e:
            logger.warning(f"EFS discovery error: {e}")

        return nodes

    def _discover_fsx(self) -> List[DiscoveryNode]:
        """Discover FSx file systems"""
        nodes = []
        try:
            fsx = self._get_client("fsx")
            response = fsx.describe_file_systems()

            for fs in response.get("FileSystems", []):
                fs_id = fs["FileSystemId"]
                nodes.append(
                    DiscoveryNode(
                        key=f"fsx:{fs_id}",
                        display_name=fs_id,
                        node_type="storage",
                        properties={
                            "service": "FSx",
                            "file_system_id": fs_id,
                            "file_system_type": fs["FileSystemType"],
                            "lifecycle": fs["Lifecycle"],
                            "storage_capacity": fs.get("StorageCapacity"),
                            "vpc_id": fs.get("VpcId"),
                        },
                        source_metadata={"arn": fs.get("ResourceARN")},
                    )
                )
        except ClientError as e:
            logger.warning(f"FSx discovery error: {e}")

        return nodes

    # ============= DATABASE SERVICES =============

    def _discover_rds(self) -> List[DiscoveryNode]:
        """Discover RDS instances and Aurora clusters"""
        nodes = []
        try:
            rds = self._get_client("rds")

            # RDS Instances
            response = rds.describe_db_instances()
            for db in response.get("DBInstances", []):
                db_id = db["DBInstanceIdentifier"]
                nodes.append(
                    DiscoveryNode(
                        key=f"rds:{db_id}",
                        display_name=db_id,
                        node_type="datastore",
                        properties={
                            "service": "RDS",
                            "db_instance_id": db_id,
                            "engine": db["Engine"],
                            "engine_version": db.get("EngineVersion"),
                            "status": db["DBInstanceStatus"],
                            "instance_class": db.get("DBInstanceClass"),
                            "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId"),
                            "endpoint": db.get("Endpoint", {}).get("Address"),
                            "port": db.get("Endpoint", {}).get("Port"),
                            "multi_az": db.get("MultiAZ"),
                            "allocated_storage": db.get("AllocatedStorage"),
                            "storage_type": db.get("StorageType"),
                            "db_subnet_group": db.get("DBSubnetGroup", {}).get("DBSubnetGroupName"),
                            "tags": self._get_tags_dict(db.get("TagList", [])),
                        },
                        source_metadata={"arn": db["DBInstanceArn"]},
                    )
                )

            # Aurora Clusters
            clusters = rds.describe_db_clusters()
            for cluster in clusters.get("DBClusters", []):
                cluster_id = cluster["DBClusterIdentifier"]
                nodes.append(
                    DiscoveryNode(
                        key=f"rds:cluster:{cluster_id}",
                        display_name=f"{cluster_id} (Cluster)",
                        node_type="datastore",
                        properties={
                            "service": "Aurora",
                            "cluster_id": cluster_id,
                            "engine": cluster["Engine"],
                            "status": cluster["Status"],
                            "endpoint": cluster.get("Endpoint"),
                            "reader_endpoint": cluster.get("ReaderEndpoint"),
                            "member_count": len(cluster.get("DBClusterMembers", [])),
                        },
                        source_metadata={"arn": cluster["DBClusterArn"]},
                    )
                )
        except ClientError as e:
            logger.warning(f"RDS discovery error: {e}")

        return nodes

    def _discover_dynamodb(self) -> List[DiscoveryNode]:
        """Discover DynamoDB tables"""
        nodes = []
        try:
            dynamodb = self._get_client("dynamodb")
            response = dynamodb.list_tables()

            for table_name in response.get("TableNames", []):
                table = dynamodb.describe_table(TableName=table_name).get("Table", {})
                nodes.append(
                    DiscoveryNode(
                        key=f"dynamodb:{table_name}",
                        display_name=table_name,
                        node_type="datastore",
                        properties={
                            "service": "DynamoDB",
                            "table_name": table_name,
                            "status": table.get("TableStatus"),
                            "item_count": table.get("ItemCount"),
                            "size_bytes": table.get("TableSizeBytes"),
                            "billing_mode": table.get("BillingModeSummary", {}).get(
                                "BillingMode"
                            ),
                        },
                        source_metadata={"arn": table.get("TableArn")},
                    )
                )
        except ClientError as e:
            logger.warning(f"DynamoDB discovery error: {e}")

        return nodes

    def _discover_redshift(self) -> List[DiscoveryNode]:
        """Discover Redshift clusters"""
        nodes = []
        try:
            redshift = self._get_client("redshift")
            response = redshift.describe_clusters()

            for cluster in response.get("Clusters", []):
                cluster_id = cluster["ClusterIdentifier"]
                nodes.append(
                    DiscoveryNode(
                        key=f"redshift:{cluster_id}",
                        display_name=cluster_id,
                        node_type="datastore",
                        properties={
                            "service": "Redshift",
                            "cluster_id": cluster_id,
                            "node_type": cluster.get("NodeType"),
                            "number_of_nodes": cluster.get("NumberOfNodes"),
                            "status": cluster.get("ClusterStatus"),
                            "database_name": cluster.get("DBName"),
                            "endpoint": cluster.get("Endpoint", {}).get("Address"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:redshift:{self.region_name}:{self._get_account_id()}:cluster:{cluster_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"Redshift discovery error: {e}")

        return nodes

    # ============= NETWORKING/CDN SERVICES =============

    def _discover_vpc(self) -> List[DiscoveryNode]:
        """Discover VPCs"""
        nodes = []
        try:
            ec2 = self._get_client("ec2")
            response = ec2.describe_vpcs()

            for vpc in response.get("Vpcs", []):
                vpc_id = vpc["VpcId"]
                name = self._get_name_tag(vpc.get("Tags", []))

                nodes.append(
                    DiscoveryNode(
                        key=f"vpc:{vpc_id}",
                        display_name=name or vpc_id,
                        node_type="network",
                        properties={
                            "service": "VPC",
                            "vpc_id": vpc_id,
                            "cidr_block": vpc.get("CidrBlock"),
                            "state": vpc.get("State"),
                            "is_default": vpc.get("IsDefault"),
                            "tags": self._get_tags_dict(vpc.get("Tags", [])),
                        },
                        source_metadata={
                            "arn": f"arn:aws:ec2:{self.region_name}:{self._get_account_id()}:vpc/{vpc_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"VPC discovery error: {e}")

        return nodes

    def _discover_load_balancers(self) -> List[DiscoveryNode]:
        """Discover ALB, NLB, and ELB load balancers"""
        nodes = []
        try:
            elb_v2 = self._get_client("elbv2")
            response = elb_v2.describe_load_balancers()

            for lb in response.get("LoadBalancers", []):
                lb_arn = lb["LoadBalancerArn"]
                lb_name = lb["LoadBalancerName"]
                lb_type = lb.get("Type", "application")

                nodes.append(
                    DiscoveryNode(
                        key=f"elb:{lb_name}",
                        display_name=lb_name,
                        node_type="network",
                        properties={
                            "service": "ELB",
                            "load_balancer_name": lb_name,
                            "load_balancer_type": lb_type,
                            "scheme": lb.get("Scheme"),
                            "state": lb.get("State", {}).get("Code"),
                            "vpc_id": lb.get("VpcId"),
                            "dns_name": lb.get("DNSName"),
                        },
                        source_metadata={"arn": lb_arn},
                    )
                )
        except ClientError as e:
            logger.warning(f"ELB discovery error: {e}")

        return nodes

    def _discover_cloudfront(self) -> List[DiscoveryNode]:
        """Discover CloudFront distributions"""
        nodes = []
        try:
            cloudfront = self._get_client("cloudfront")
            response = cloudfront.list_distributions()

            for dist in response.get("DistributionList", {}).get("Items", []):
                dist_id = dist["Id"]
                domain = dist.get("DomainName")

                nodes.append(
                    DiscoveryNode(
                        key=f"cloudfront:{dist_id}",
                        display_name=domain or dist_id,
                        node_type="network",
                        properties={
                            "service": "CloudFront",
                            "distribution_id": dist_id,
                            "domain_name": domain,
                            "status": dist.get("Status"),
                            "enabled": dist.get("Enabled"),
                            "origins": [
                                o.get("DomainName")
                                for o in dist.get("Origins", {}).get("Items", [])
                            ],
                        },
                        source_metadata={
                            "arn": f"arn:aws:cloudfront::{self._get_account_id()}:distribution/{dist_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"CloudFront discovery error: {e}")

        return nodes

    def _discover_direct_connect(self) -> List[DiscoveryNode]:
        """Discover Direct Connect connections"""
        nodes = []
        try:
            dx = self._get_client("directconnect")
            response = dx.describe_connections()

            for conn in response.get("connections", []):
                conn_id = conn["connectionId"]
                conn_name = conn.get("connectionName", conn_id)

                nodes.append(
                    DiscoveryNode(
                        key=f"directconnect:{conn_id}",
                        display_name=conn_name,
                        node_type="network",
                        properties={
                            "service": "DirectConnect",
                            "connection_id": conn_id,
                            "bandwidth": conn.get("bandwidth"),
                            "location": conn.get("location"),
                            "connection_state": conn.get("connectionState"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:directconnect:{self.region_name}:{self._get_account_id()}:dxcon:{conn_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"Direct Connect discovery error: {e}")

        return nodes

    # ============= SECURITY/IAM SERVICES =============

    def _discover_iam_roles(self) -> List[DiscoveryNode]:
        """Discover IAM roles"""
        nodes = []
        try:
            iam = self._get_client("iam")
            response = iam.list_roles()

            for role in response.get("Roles", []):
                role_name = role["RoleName"]
                nodes.append(
                    DiscoveryNode(
                        key=f"iam:role:{role_name}",
                        display_name=role_name,
                        node_type="security",
                        properties={
                            "service": "IAM",
                            "resource_type": "role",
                            "role_name": role_name,
                            "created_date": (
                                role.get("CreateDate").isoformat()
                                if role.get("CreateDate")
                                else None
                            ),
                        },
                        source_metadata={"arn": role["Arn"]},
                    )
                )
        except ClientError as e:
            logger.warning(f"IAM Roles discovery error: {e}")

        return nodes

    def _discover_kms(self) -> List[DiscoveryNode]:
        """Discover KMS keys"""
        nodes = []
        try:
            kms = self._get_client("kms")
            response = kms.list_keys()

            for key in response.get("Keys", []):
                key_id = key["KeyId"]
                key_metadata = kms.describe_key(KeyId=key_id).get("KeyMetadata", {})

                if key_metadata.get("KeyManager") == "CUSTOMER":
                    nodes.append(
                        DiscoveryNode(
                            key=f"kms:{key_id}",
                            display_name=key_metadata.get("Description") or key_id,
                            node_type="security",
                            properties={
                                "service": "KMS",
                                "key_id": key_id,
                                "key_state": key_metadata.get("KeyState"),
                                "description": key_metadata.get("Description"),
                            },
                            source_metadata={"arn": key_metadata.get("Arn")},
                        )
                    )
        except ClientError as e:
            logger.warning(f"KMS discovery error: {e}")

        return nodes

    def _discover_secrets_manager(self) -> List[DiscoveryNode]:
        """Discover Secrets Manager secrets"""
        nodes = []
        try:
            secrets = self._get_client("secretsmanager")
            response = secrets.list_secrets()

            for secret in response.get("SecretList", []):
                secret_name = secret["Name"]
                nodes.append(
                    DiscoveryNode(
                        key=f"secretsmanager:{secret_name}",
                        display_name=secret_name,
                        node_type="security",
                        properties={
                            "service": "SecretsManager",
                            "secret_name": secret_name,
                            "created_date": (
                                secret.get("CreatedDate").isoformat()
                                if secret.get("CreatedDate")
                                else None
                            ),
                        },
                        source_metadata={"arn": secret.get("ARN")},
                    )
                )
        except ClientError as e:
            logger.warning(f"Secrets Manager discovery error: {e}")

        return nodes

    def _discover_directory_service(self) -> List[DiscoveryNode]:
        """Discover AWS Directory Service directories"""
        nodes = []
        try:
            ds = self._get_client("ds")
            response = ds.describe_directories()

            for directory in response.get("DirectoryDescriptions", []):
                dir_id = directory["DirectoryId"]
                dir_name = directory.get("Name", dir_id)

                nodes.append(
                    DiscoveryNode(
                        key=f"directoryservice:{dir_id}",
                        display_name=dir_name,
                        node_type="security",
                        properties={
                            "service": "DirectoryService",
                            "directory_id": dir_id,
                            "directory_type": directory.get("Type"),
                            "status": directory.get("Stage"),
                            "vpc_id": directory.get("VpcSettings", {}).get("VpcId"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:ds:{self.region_name}:{self._get_account_id()}:directory/{dir_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"Directory Service discovery error: {e}")

        return nodes

    # ============= OBSERVABILITY/OPS SERVICES =============

    def _discover_cloudwatch(self) -> List[DiscoveryNode]:
        """Discover CloudWatch log groups"""
        nodes = []
        try:
            logs = self._get_client("logs")
            response = logs.describe_log_groups()

            for log_group in response.get("logGroups", []):
                log_group_name = log_group["logGroupName"]
                nodes.append(
                    DiscoveryNode(
                        key=f"cloudwatch:loggroup:{log_group_name}",
                        display_name=log_group_name,
                        node_type="observability",
                        properties={
                            "service": "CloudWatch",
                            "log_group_name": log_group_name,
                            "retention_in_days": log_group.get("retentionInDays"),
                            "stored_bytes": log_group.get("storedBytes"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:logs:{self.region_name}:{self._get_account_id()}:log-group:{log_group_name}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"CloudWatch discovery error: {e}")

        return nodes

    def _discover_cloudtrail(self) -> List[DiscoveryNode]:
        """Discover CloudTrail trails"""
        nodes = []
        try:
            cloudtrail = self._get_client("cloudtrail")
            response = cloudtrail.describe_trails()

            for trail in response.get("trailList", []):
                trail_name = trail.get(
                    "Name", trail.get("TrailArn", "").split(":trail/")[-1]
                )
                nodes.append(
                    DiscoveryNode(
                        key=f"cloudtrail:{trail_name}",
                        display_name=trail_name,
                        node_type="observability",
                        properties={
                            "service": "CloudTrail",
                            "trail_name": trail_name,
                            "s3_bucket_name": trail.get("S3BucketName"),
                            "is_multi_region_trail": trail.get("IsMultiRegionTrail"),
                            "home_region": trail.get("HomeRegion"),
                        },
                        source_metadata={"arn": trail.get("TrailArn")},
                    )
                )
        except ClientError as e:
            logger.warning(f"CloudTrail discovery error: {e}")

        return nodes

    def _discover_systems_manager(self) -> List[DiscoveryNode]:
        """Discover Systems Manager resources"""
        nodes = []
        try:
            ssm = self._get_client("ssm")

            # Parameters
            response = ssm.describe_parameters()
            for param in response.get("Parameters", []):
                param_name = param["Name"]
                nodes.append(
                    DiscoveryNode(
                        key=f"ssm:parameter:{param_name}",
                        display_name=param_name,
                        node_type="observability",
                        properties={
                            "service": "SystemsManager",
                            "resource_type": "parameter",
                            "parameter_name": param_name,
                            "type": param.get("Type"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:ssm:{self.region_name}:{self._get_account_id()}:parameter{param_name}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"Systems Manager discovery error: {e}")

        return nodes

    # ============= INTEGRATION SERVICES =============

    def _discover_sqs(self) -> List[DiscoveryNode]:
        """Discover SQS queues"""
        nodes = []
        try:
            sqs = self._get_client("sqs")
            response = sqs.list_queues()

            for queue_url in response.get("QueueUrls", []):
                queue_name = queue_url.split("/")[-1]
                nodes.append(
                    DiscoveryNode(
                        key=f"sqs:{queue_name}",
                        display_name=queue_name,
                        node_type="integration",
                        properties={
                            "service": "SQS",
                            "queue_name": queue_name,
                            "queue_url": queue_url,
                        },
                        source_metadata={
                            "arn": f"arn:aws:sqs:{self.region_name}:{self._get_account_id()}:{queue_name}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"SQS discovery error: {e}")

        return nodes

    def _discover_sns(self) -> List[DiscoveryNode]:
        """Discover SNS topics"""
        nodes = []
        try:
            sns = self._get_client("sns")
            response = sns.list_topics()

            for topic in response.get("Topics", []):
                topic_arn = topic["TopicArn"]
                topic_name = topic_arn.split(":")[-1]

                nodes.append(
                    DiscoveryNode(
                        key=f"sns:{topic_name}",
                        display_name=topic_name,
                        node_type="integration",
                        properties={
                            "service": "SNS",
                            "topic_name": topic_name,
                            "topic_arn": topic_arn,
                        },
                        source_metadata={"arn": topic_arn},
                    )
                )
        except ClientError as e:
            logger.warning(f"SNS discovery error: {e}")

        return nodes

    def _discover_eventbridge(self) -> List[DiscoveryNode]:
        """Discover EventBridge rules"""
        nodes = []
        try:
            events = self._get_client("events")
            response = events.list_rules()

            for rule in response.get("Rules", []):
                rule_name = rule["Name"]
                nodes.append(
                    DiscoveryNode(
                        key=f"eventbridge:rule:{rule_name}",
                        display_name=rule_name,
                        node_type="integration",
                        properties={
                            "service": "EventBridge",
                            "rule_name": rule_name,
                            "state": rule.get("State"),
                            "event_pattern": rule.get("EventPattern"),
                            "schedule_expression": rule.get("ScheduleExpression"),
                        },
                        source_metadata={
                            "arn": f"arn:aws:events:{self.region_name}:{self._get_account_id()}:rule/{rule_name}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"EventBridge discovery error: {e}")

        return nodes

    def _discover_api_gateway(self) -> List[DiscoveryNode]:
        """Discover API Gateway APIs"""
        nodes = []
        try:
            apigw = self._get_client("apigateway")
            response = apigw.get_rest_apis()

            for api in response.get("items", []):
                api_id = api["id"]
                api_name = api.get("name", api_id)

                nodes.append(
                    DiscoveryNode(
                        key=f"apigateway:{api_id}",
                        display_name=api_name,
                        node_type="integration",
                        properties={
                            "service": "APIGateway",
                            "api_id": api_id,
                            "api_name": api_name,
                            "protocol": "REST",
                        },
                        source_metadata={
                            "arn": f"arn:aws:apigateway:{self.region_name}::/restapis/{api_id}"
                        },
                    )
                )
        except ClientError as e:
            logger.warning(f"API Gateway discovery error: {e}")

        return nodes

    # ============= RELATIONSHIP DETECTION =============

    def _detect_relationships(self, nodes: List[DiscoveryNode]) -> List[DiscoveryEdge]:
        """Detect relationships between resources"""
        edges = []
        node_map = {node.key: node for node in nodes}

        try:
            ec2 = self._get_client("ec2")

            # EC2 -> EBS Volume attachments
            for node in nodes:
                if node.properties.get("service") == "EC2":
                    ebs_attached = node.properties.get("attached_to", [])
                    for vol_id in node.properties.get("attached_to", []):
                        ebs_key = f"ebs:{vol_id}"
                        if ebs_key in node_map:
                            edges.append(
                                DiscoveryEdge(
                                    from_node_key=node.key,
                                    to_node_key=ebs_key,
                                    edge_type="uses",
                                    properties={"relationship": "storage_attachment"},
                                )
                            )

            # Lambda -> VPC
            for node in nodes:
                if node.properties.get("service") == "Lambda":
                    vpc_id = node.properties.get("vpc_id")
                    if vpc_id:
                        vpc_key = f"vpc:{vpc_id}"
                        if vpc_key in node_map:
                            edges.append(
                                DiscoveryEdge(
                                    from_node_key=node.key,
                                    to_node_key=vpc_key,
                                    edge_type="runs_in",
                                    properties={"relationship": "network_execution"},
                                )
                            )

            # EC2 -> VPC
            for node in nodes:
                if node.properties.get("service") == "EC2":
                    vpc_id = node.properties.get("vpc_id")
                    if vpc_id:
                        vpc_key = f"vpc:{vpc_id}"
                        if vpc_key in node_map:
                            edges.append(
                                DiscoveryEdge(
                                    from_node_key=vpc_key,
                                    to_node_key=node.key,
                                    edge_type="contains",
                                    properties={"relationship": "network_membership"},
                                )
                            )

            # Load Balancer -> EC2
            for node in nodes:
                if node.properties.get("service") == "ELB":
                    vpc_id = node.properties.get("vpc_id")
                    # Find EC2 instances in same VPC
                    for ec2_node in nodes:
                        if ec2_node.properties.get("service") == "EC2":
                            if ec2_node.properties.get("vpc_id") == vpc_id:
                                edges.append(
                                    DiscoveryEdge(
                                        from_node_key=node.key,
                                        to_node_key=ec2_node.key,
                                        edge_type="routes_to",
                                        properties={"relationship": "load_balancing"},
                                    )
                                )

            # CloudFront -> S3 origins
            for node in nodes:
                if node.properties.get("service") == "CloudFront":
                    origins = node.properties.get("origins", [])
                    for origin in origins:
                        if ".s3." in origin:
                            bucket_name = origin.split(".")[0]
                            s3_key = f"s3:{bucket_name}"
                            if s3_key in node_map:
                                edges.append(
                                    DiscoveryEdge(
                                        from_node_key=node.key,
                                        to_node_key=s3_key,
                                        edge_type="originates_from",
                                        properties={"relationship": "cdn_origin"},
                                    )
                                )

        except Exception as e:
            logger.warning(f"Relationship detection error: {e}")

        return edges
