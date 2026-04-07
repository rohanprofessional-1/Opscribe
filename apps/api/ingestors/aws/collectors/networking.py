"""
Networking service collectors: VPC, ELB, CloudFront, DirectConnect.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class VPCCollector(BaseCollector):
    """Discover VPCs, subnets, and security groups."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "VPC")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        ec2 = self._client("ec2")

        # 1. Identify Default VPCs
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        default_vpc_ids = {v["VpcId"] for v in vpcs if v.get("IsDefault")}
        
        # --- VPCs ---
        for vpc in vpcs:
            vid = vpc["VpcId"]
            if vid in default_vpc_ids:
                continue

            name = self._get_name_tag(vpc.get("Tags", []))
            arn = f"arn:aws:ec2:{self.region}:{self.account_id}:vpc/{vid}"

            nodes.append(TopologyNode(
                uid=self._make_uid("vpc", vid),
                provider="aws",
                service="VPC",
                resource_type="network/vpc",
                category="network",
                name=name or vid,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(vpc.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": vid,
                    "name_tag": name,
                },
                properties={
                    "vpc_id": vid,
                    "cidr_block": vpc.get("CidrBlock"),
                    "state": vpc.get("State"),
                    "is_default": vpc.get("IsDefault"),
                },
                raw=vpc,
            ))

        # --- Subnets ---
        for subnet in ec2.describe_subnets().get("Subnets", []):
            sid = subnet["SubnetId"]
            vpc_id = subnet.get("VpcId")
            
            # Skip subnets in default VPCs
            if vpc_id in default_vpc_ids:
                continue

            name = self._get_name_tag(subnet.get("Tags", []))
            arn = f"arn:aws:ec2:{self.region}:{self.account_id}:subnet/{sid}"

            nodes.append(TopologyNode(
                uid=self._make_uid("subnet", sid),
                provider="aws",
                service="VPC",
                resource_type="network/subnet",
                category="network",
                name=name or sid,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(subnet.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": sid,
                    "name_tag": name,
                },
                properties={
                    "subnet_id": sid,
                    "vpc_id": vpc_id,
                    "cidr_block": subnet.get("CidrBlock"),
                    "availability_zone": subnet.get("AvailabilityZone"),
                    "state": subnet.get("State"),
                    "available_ips": subnet.get("AvailableIpAddressCount"),
                },
                raw=subnet,
            ))

        # --- Security Groups ---
        for sg in ec2.describe_security_groups().get("SecurityGroups", []):
            sgid = sg["GroupId"]
            vpc_id = sg.get("VpcId")
            
            # Skip security groups in default VPCs
            if vpc_id in default_vpc_ids:
                continue

            name = sg.get("GroupName", sgid)
            arn = f"arn:aws:ec2:{self.region}:{self.account_id}:security-group/{sgid}"

            nodes.append(TopologyNode(
                uid=self._make_uid("sg", sgid),
                provider="aws",
                service="VPC",
                resource_type="network/security_group",
                category="network",
                name=name,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(sg.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": sgid,
                    "name_tag": name,
                },
                properties={
                    "group_id": sgid,
                    "group_name": sg.get("GroupName"),
                    "vpc_id": vpc_id,
                    "description": sg.get("Description"),
                    "ingress_rule_count": len(sg.get("IpPermissions", [])),
                    "egress_rule_count": len(sg.get("IpPermissionsEgress", [])),
                },
                raw=sg,
            ))

        return nodes


class ELBCollector(BaseCollector):
    """Discover ALB/NLB/GLB load balancers."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "ELB")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        elbv2 = self._client("elbv2")
        response = elbv2.describe_load_balancers()

        for lb in response.get("LoadBalancers", []):
            lb_arn = lb["LoadBalancerArn"]
            lb_name = lb["LoadBalancerName"]
            dns = lb.get("DNSName")

            nodes.append(TopologyNode(
                uid=self._make_uid("elb", lb_name),
                provider="aws",
                service="ELB",
                resource_type="network/load_balancer",
                category="network",
                name=lb_name,
                region=self.region,
                account_id=self.account_id,
                tags={},
                merge_hints={
                    "arn": lb_arn,
                    "resource_id": lb_name,
                    "name_tag": lb_name,
                    "dns_name": dns,
                },
                properties={
                    "load_balancer_name": lb_name,
                    "load_balancer_type": lb.get("Type", "application"),
                    "scheme": lb.get("Scheme"),
                    "state": lb.get("State", {}).get("Code"),
                    "vpc_id": lb.get("VpcId"),
                    "dns_name": dns,
                    "availability_zones": [
                        az.get("ZoneName") for az in lb.get("AvailabilityZones", [])
                    ],
                },
                raw=lb,
            ))
        return nodes


class CloudFrontCollector(BaseCollector):
    """Discover CloudFront distributions."""

    IS_GLOBAL = True

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "CloudFront")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        cf = self._client("cloudfront")
        response = cf.list_distributions()

        for dist in response.get("DistributionList", {}).get("Items", []):
            did = dist["Id"]
            domain = dist.get("DomainName")
            arn = f"arn:aws:cloudfront::{self.account_id}:distribution/{did}"

            nodes.append(TopologyNode(
                uid=self._make_uid("cloudfront", did),
                provider="aws",
                service="CloudFront",
                resource_type="network/cdn",
                category="network",
                name=domain or did,
                region="global",
                account_id=self.account_id,
                tags={},
                merge_hints={
                    "arn": arn,
                    "resource_id": did,
                    "dns_name": domain,
                },
                properties={
                    "distribution_id": did,
                    "domain_name": domain,
                    "status": dist.get("Status"),
                    "enabled": dist.get("Enabled"),
                    "origins": [
                        o.get("DomainName") for o in dist.get("Origins", {}).get("Items", [])
                    ],
                },
                raw=dist,
            ))
        return nodes


class DirectConnectCollector(BaseCollector):
    """Discover Direct Connect connections."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "DirectConnect")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        dx = self._client("directconnect")
        response = dx.describe_connections()

        for conn in response.get("connections", []):
            cid = conn["connectionId"]
            cname = conn.get("connectionName", cid)
            arn = f"arn:aws:directconnect:{self.region}:{self.account_id}:dxcon:{cid}"

            nodes.append(TopologyNode(
                uid=self._make_uid("directconnect", cid),
                provider="aws",
                service="DirectConnect",
                resource_type="network/dedicated_connection",
                category="network",
                name=cname,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(conn.get("tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": cid,
                    "name_tag": cname,
                },
                properties={
                    "connection_id": cid,
                    "bandwidth": conn.get("bandwidth"),
                    "location": conn.get("location"),
                    "connection_state": conn.get("connectionState"),
                },
                raw=conn,
            ))
        return nodes
