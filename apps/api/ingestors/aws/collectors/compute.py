"""
Compute service collectors: EC2, Lambda, ECS, EKS.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class EC2Collector(BaseCollector):
    """Discover EC2 instances."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "EC2")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ec2 = self._client("ec2")
        paginator = ec2.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    iid = inst["InstanceId"]
                    name = self._get_name_tag(inst.get("Tags", []))
                    arn = f"arn:aws:ec2:{self.region}:{self.account_id}:instance/{iid}"

                    nodes.append(TopologyNode(
                        uid=self._make_uid("ec2", iid),
                        provider="aws",
                        service="EC2",
                        resource_type="compute/instance",
                        category="compute",
                        name=name or iid,
                        region=self.region,
                        account_id=self.account_id,
                        tags=self._get_tags_dict(inst.get("Tags", [])),
                        merge_hints={
                            "arn": arn,
                            "resource_id": iid,
                            "name_tag": name,
                            "dns_name": inst.get("PrivateDnsName"),
                            "public_dns_name": inst.get("PublicDnsName"),
                        },
                        properties={
                            "instance_type": inst["InstanceType"],
                            "state": inst["State"]["Name"],
                            "private_ip": inst.get("PrivateIpAddress"),
                            "public_ip": inst.get("PublicIpAddress"),
                            "availability_zone": inst.get("Placement", {}).get("AvailabilityZone"),
                            "vpc_id": inst.get("VpcId"),
                            "subnet_id": inst.get("SubnetId"),
                            "security_groups": [sg["GroupId"] for sg in inst.get("SecurityGroups", [])],
                            "image_id": inst.get("ImageId"),
                            "iam_instance_profile": inst.get("IamInstanceProfile", {}).get("Arn"),
                            "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None,
                            "monitoring": inst.get("Monitoring", {}).get("State"),
                        },
                        raw=inst,
                    ))
        return nodes


class LambdaCollector(BaseCollector):
    """Discover Lambda functions."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "Lambda")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        client = self._client("lambda")
        paginator = client.get_paginator("list_functions")

        for page in paginator.paginate():
            for func in page.get("Functions", []):
                fname = func["FunctionName"]
                arn = func["FunctionArn"]

                nodes.append(TopologyNode(
                    uid=self._make_uid("lambda", fname),
                    provider="aws",
                    service="Lambda",
                    resource_type="compute/function",
                    category="compute",
                    name=fname,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},  # list_functions doesn't return tags
                    merge_hints={
                        "arn": arn,
                        "resource_id": fname,
                        "name_tag": fname,
                    },
                    properties={
                        "runtime": func.get("Runtime"),
                        "handler": func.get("Handler"),
                        "memory_size": func.get("MemorySize"),
                        "timeout": func.get("Timeout"),
                        "vpc_id": func.get("VpcConfig", {}).get("VpcId"),
                        "subnet_ids": func.get("VpcConfig", {}).get("SubnetIds", []),
                        "security_group_ids": func.get("VpcConfig", {}).get("SecurityGroupIds", []),
                        "role_arn": func.get("Role"),
                        "description": func.get("Description"),
                        "last_modified": func.get("LastModified"),
                        "layers": [layer.get("Arn") for layer in func.get("Layers", [])],
                        "environment": func.get("Environment", {}).get("Variables", {}),
                    },
                    raw=func,
                ))
        return nodes


class ECSCollector(BaseCollector):
    """Discover ECS clusters and services."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "ECS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ecs = self._client("ecs")
        clusters = ecs.list_clusters().get("clusterArns", [])

        for cluster_arn in clusters:
            cluster_name = cluster_arn.split("/")[-1]

            # Describe cluster for full details
            desc = ecs.describe_clusters(clusters=[cluster_arn]).get("clusters", [])
            cluster_raw = desc[0] if desc else {}

            nodes.append(TopologyNode(
                uid=self._make_uid("ecs", f"cluster/{cluster_name}"),
                provider="aws",
                service="ECS",
                resource_type="compute/container_cluster",
                category="compute",
                name=cluster_name,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(cluster_raw.get("tags", [])),
                merge_hints={
                    "arn": cluster_arn,
                    "resource_id": cluster_name,
                    "name_tag": cluster_name,
                },
                properties={
                    "cluster_name": cluster_name,
                    "status": cluster_raw.get("status"),
                    "running_tasks_count": cluster_raw.get("runningTasksCount"),
                    "active_services_count": cluster_raw.get("activeServicesCount"),
                },
                raw=cluster_raw,
            ))

            # Services within this cluster
            services = ecs.list_services(cluster=cluster_arn).get("serviceArns", [])
            if services:
                svc_details = ecs.describe_services(cluster=cluster_arn, services=services).get("services", [])
                for svc in svc_details:
                    svc_name = svc.get("serviceName", svc.get("serviceArn", "").split("/")[-1])
                    nodes.append(TopologyNode(
                        uid=self._make_uid("ecs", f"service/{cluster_name}/{svc_name}"),
                        provider="aws",
                        service="ECS",
                        resource_type="compute/container_service",
                        category="compute",
                        name=f"{cluster_name}/{svc_name}",
                        region=self.region,
                        account_id=self.account_id,
                        tags=self._get_tags_dict(svc.get("tags", [])),
                        merge_hints={
                            "arn": svc.get("serviceArn", ""),
                            "resource_id": svc_name,
                            "name_tag": svc_name,
                        },
                        properties={
                            "cluster_name": cluster_name,
                            "service_name": svc_name,
                            "status": svc.get("status"),
                            "desired_count": svc.get("desiredCount"),
                            "running_count": svc.get("runningCount"),
                            "launch_type": svc.get("launchType"),
                            "task_definition": svc.get("taskDefinition"),
                        },
                        raw=svc,
                    ))
        return nodes


class EKSCollector(BaseCollector):
    """Discover EKS clusters."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "EKS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        eks = self._client("eks")
        clusters = eks.list_clusters().get("clusters", [])

        for cluster_name in clusters:
            cluster = eks.describe_cluster(name=cluster_name).get("cluster", {})
            arn = cluster.get("arn", "")

            nodes.append(TopologyNode(
                uid=self._make_uid("eks", cluster_name),
                provider="aws",
                service="EKS",
                resource_type="compute/kubernetes_cluster",
                category="compute",
                name=cluster_name,
                region=self.region,
                account_id=self.account_id,
                tags=cluster.get("tags", {}),
                merge_hints={
                    "arn": arn,
                    "resource_id": cluster_name,
                    "name_tag": cluster_name,
                    "endpoint": cluster.get("endpoint"),
                },
                properties={
                    "cluster_name": cluster_name,
                    "version": cluster.get("version"),
                    "status": cluster.get("status"),
                    "vpc_id": cluster.get("resourcesVpcConfig", {}).get("vpcId"),
                    "platform_version": cluster.get("platformVersion"),
                    "role_arn": cluster.get("roleArn"),
                },
                raw=cluster,
            ))
        return nodes
