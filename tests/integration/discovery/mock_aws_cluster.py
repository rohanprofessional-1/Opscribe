"""
Mock AWS Infrastructure Factory

Creates realistic mock AWS infrastructure for testing.
Includes VPC, subnets, EC2 instances, RDS, S3, and SQS.
"""

from typing import Dict, Any, List
from datetime import datetime
import hashlib


class MockAWSCluster:
    """Factory for creating consistent mock AWS infrastructure"""

    def __init__(self, service_name: str = "opscribe-test"):
        self.service_name = service_name
        self.account_id = "123456789012"
        self.region = "us-east-1"
        self.vpc_id = f"vpc-{self._generate_id('vpc')}"
        # Ensure unique subnet IDs
        self.subnet_ids = [
            f"subnet-{self._generate_id('subnet-a')}",
            f"subnet-{self._generate_id('subnet-b')}"
        ]
        self.sg_id = f"sg-{self._generate_id('sg')}"
        # Ensure unique EC2 instance IDs
        self.ec2_instance_ids = [
            f"i-{self._generate_id('ec2-instance-0')}",
            f"i-{self._generate_id('ec2-instance-1')}"
        ]
        self.rds_instance_id = f"{service_name}-db"
        self.s3_bucket_name = f"{service_name}-terraform-state"
        self.sqs_queue_name = f"{service_name}-events"

    def _generate_id(self, seed: str) -> str:
        """Generate a deterministic mock AWS ID from a seed"""
        # Use deterministic hash for consistent IDs
        hash_obj = hashlib.md5(seed.encode())
        return hash_obj.hexdigest()[:16]

    def _create_tag(self, name: str) -> Dict[str, str]:
        """Create a standard tag dict"""
        return {"Key": "Name", "Value": name}

    def _create_tags_list(self, *names: str) -> List[Dict[str, str]]:
        """Create tags for a resource"""
        tags = [
            {"Key": "Service", "Value": self.service_name},
            {"Key": "Environment", "Value": "test"},
            {"Key": "CreatedBy", "Value": "opscribe-test"},
        ]
        for name in names:
            tags.append({"Key": "Name", "Value": name})
        return tags

    # ============= VPC & Networking =============

    def vpc(self) -> Dict[str, Any]:
        """Mock VPC response"""
        return {
            "VpcId": self.vpc_id,
            "CidrBlock": "10.0.0.0/16",
            "State": "available",
            "IsDefault": False,
            "Tags": self._create_tags_list(f"{self.service_name}-vpc"),
        }

    def subnets(self) -> List[Dict[str, Any]]:
        """Mock subnet responses"""
        return [
            {
                "SubnetId": self.subnet_ids[0],
                "VpcId": self.vpc_id,
                "CidrBlock": "10.0.1.0/24",
                "AvailabilityZone": f"{self.region}a",
                "State": "available",
                "Tags": self._create_tags_list(f"{self.service_name}-subnet-1"),
            },
            {
                "SubnetId": self.subnet_ids[1],
                "VpcId": self.vpc_id,
                "CidrBlock": "10.0.2.0/24",
                "AvailabilityZone": f"{self.region}b",
                "State": "available",
                "Tags": self._create_tags_list(f"{self.service_name}-subnet-2"),
            },
        ]

    # ============= EC2 Instances =============

    def ec2_instances(self) -> List[Dict[str, Any]]:
        """Mock EC2 instance responses"""
        return [
            {
                "InstanceId": self.ec2_instance_ids[0],
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.1.10",
                "PublicIpAddress": "54.123.45.67",
                "VpcId": self.vpc_id,
                "SubnetId": self.subnet_ids[0],
                "Placement": {"AvailabilityZone": f"{self.region}a"},
                "SecurityGroups": [{"GroupId": self.sg_id}],
                "Tags": self._create_tags_list(f"{self.service_name}-app-server-1"),
                "OwnerId": self.account_id,
            },
            {
                "InstanceId": self.ec2_instance_ids[1],
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.2.10",
                "PublicIpAddress": "54.234.56.78",
                "VpcId": self.vpc_id,
                "SubnetId": self.subnet_ids[1],
                "Placement": {"AvailabilityZone": f"{self.region}b"},
                "SecurityGroups": [{"GroupId": self.sg_id}],
                "Tags": self._create_tags_list(f"{self.service_name}-app-server-2"),
                "OwnerId": self.account_id,
            },
        ]

    def describe_instances_response(self) -> Dict[str, Any]:
        """Complete EC2 describe_instances response"""
        instances = self.ec2_instances()
        return {
            "Reservations": [
                {
                    "ReservationId": "r-0123456789abcdef0",
                    "OwnerId": self.account_id,
                    "Instances": instances,
                }
            ]
        }

    # ============= RDS =============

    def rds_instance(self) -> Dict[str, Any]:
        """Mock RDS instance response"""
        return {
            "DBInstanceIdentifier": self.rds_instance_id,
            "DBInstanceClass": "db.t3.micro",
            "Engine": "postgres",
            "EngineVersion": "14.7",
            "DBInstanceStatus": "available",
            "MasterUsername": "admin",
            "DBName": "opscribedb",
            "Endpoint": {
                "Address": f"{self.rds_instance_id}.c9akciq32.{self.region}.rds.amazonaws.com",
                "Port": 5432,
                "HostedZoneId": "Z2R2ITUGPM61AM",
            },
            "AllocatedStorage": 20,
            "StorageType": "gp2",
            "DBSubnetGroup": {
                "DBSubnetGroupName": f"{self.service_name}-db-subnet",
                "DBSubnetGroupDescription": "Subnet group for Opscribe",
                "VpcId": self.vpc_id,
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {"SubnetIdentifier": sid, "SubnetAvailabilityZone": {"Name": f"{self.region}a"}}
                    for sid in self.subnet_ids
                ],
            },
            "DBInstanceArn": f"arn:aws:rds:{self.region}:{self.account_id}:db:{self.rds_instance_id}",
            "TagList": self._create_tags_list(f"{self.service_name}-database"),
        }

    def describe_db_instances_response(self) -> Dict[str, Any]:
        """Complete RDS describe_db_instances response"""
        return {"DBInstances": [self.rds_instance()]}

    # ============= S3 =============

    def s3_bucket(self) -> Dict[str, Any]:
        """Mock S3 bucket response"""
        return {
            "Name": self.s3_bucket_name,
            "CreationDate": datetime(2024, 1, 15),
            "Tags": self._create_tags_list(f"{self.service_name}-terraform-bucket"),
        }

    def s3_bucket_with_terraform_state(self) -> Dict[str, Any]:
        """S3 bucket contents with Terraform state file"""
        bucket = self.s3_bucket()
        return {
            **bucket,
            "Contents": [
                {
                    "Key": "terraform/state/main.tfstate",
                    "LastModified": datetime(2024, 3, 5),
                    "Size": 15234,
                }
            ],
        }

    def list_buckets_response(self) -> Dict[str, Any]:
        """Complete S3 list_buckets response"""
        return {"Buckets": [self.s3_bucket()]}

    def get_bucket_tagging_response(self) -> Dict[str, Any]:
        """S3 bucket tagging response"""
        return {
            "TagSet": self._create_tags_list(f"{self.service_name}-terraform-bucket")
        }

    # ============= SQS =============

    def sqs_queue(self) -> str:
        """Mock SQS queue URL"""
        return f"https://sqs.{self.region}.amazonaws.com/{self.account_id}/{self.sqs_queue_name}"

    def list_queues_response(self) -> Dict[str, Any]:
        """Complete SQS list_queues response"""
        return {"QueueUrls": [self.sqs_queue()]}

    def get_queue_attributes_response(self) -> Dict[str, Any]:
        """SQS queue attributes response"""
        return {
            "Attributes": {
                "QueueArn": f"arn:aws:sqs:{self.region}:{self.account_id}:{self.sqs_queue_name}",
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "0",
                "ApproximateNumberOfMessagesDelayed": "0",
                "CreatedTimestamp": str(int(datetime(2024, 1, 15).timestamp())),
                "LastModifiedTimestamp": str(int(datetime.now().timestamp())),
                "VisibilityTimeout": "30",
                "MessageRetentionPeriod": "345600",
                "ReceiveMessageWaitTimeSeconds": "0",
                "RedrivePolicy": "{}",
                "Tags": {
                    "Service": self.service_name,
                    "Environment": "test",
                },
            }
        }

    # ============= Summary =============

    def summary(self) -> Dict[str, Any]:
        """Get summary of all mock infrastructure"""
        return {
            "service_name": self.service_name,
            "account_id": self.account_id,
            "region": self.region,
            "vpc": {
                "vpc_id": self.vpc_id,
                "cidr": "10.0.0.0/16",
            },
            "subnets": [
                {
                    "subnet_id": self.subnet_ids[0],
                    "cidr": "10.0.1.0/24",
                    "az": f"{self.region}a",
                },
                {
                    "subnet_id": self.subnet_ids[1],
                    "cidr": "10.0.2.0/24",
                    "az": f"{self.region}b",
                },
            ],
            "ec2_instances": [
                {
                    "instance_id": self.ec2_instance_ids[0],
                    "private_ip": "10.0.1.10",
                    "subnet": self.subnet_ids[0],
                },
                {
                    "instance_id": self.ec2_instance_ids[1],
                    "private_ip": "10.0.2.10",
                    "subnet": self.subnet_ids[1],
                },
            ],
            "rds": {
                "instance_id": self.rds_instance_id,
                "engine": "postgres",
            },
            "s3": {
                "bucket_name": self.s3_bucket_name,
                "has_terraform_state": True,
            },
            "sqs": {
                "queue_name": self.sqs_queue_name,
                "queue_url": self.sqs_queue(),
            },
        }

    def print_summary(self):
        """Print infrastructure summary in readable format"""
        summary = self.summary()
        print(f"\n{'='*60}")
        print(f"Mock AWS Cluster: {summary['service_name']}")
        print(f"{'='*60}")
        print(f"\nAccount ID: {summary['account_id']}")
        print(f"Region: {summary['region']}\n")

        print("VPC:")
        print(f"  ID: {summary['vpc']['vpc_id']}")
        print(f"  CIDR: {summary['vpc']['cidr']}\n")

        print("Subnets:")
        for subnet in summary["subnets"]:
            print(f"  {subnet['subnet_id']}")
            print(f"    CIDR: {subnet['cidr']}")
            print(f"    AZ: {subnet['az']}\n")

        print("EC2 Instances:")
        for ec2 in summary["ec2_instances"]:
            print(f"  {ec2['instance_id']}")
            print(f"    IP: {ec2['private_ip']}")
            print(f"    Subnet: {ec2['subnet']}\n")

        print("RDS:")
        print(f"  Instance: {summary['rds']['instance_id']}")
        print(f"  Engine: {summary['rds']['engine']}\n")

        print("S3:")
        print(f"  Bucket: {summary['s3']['bucket_name']}\n")

        print("SQS:")
        print(f"  Queue: {summary['sqs']['queue_name']}\n")
        print(f"{'='*60}\n")
