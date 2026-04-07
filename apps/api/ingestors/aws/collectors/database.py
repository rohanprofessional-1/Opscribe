"""
Database service collectors: RDS, DynamoDB, Redshift.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class RDSCollector(BaseCollector):
    """Discover RDS instances and Aurora clusters."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "RDS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        rds = self._client("rds")

        # --- RDS Instances ---
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                dbid = db["DBInstanceIdentifier"]
                arn = db["DBInstanceArn"]
                endpoint = db.get("Endpoint", {}).get("Address")

                nodes.append(TopologyNode(
                    uid=self._make_uid("rds", dbid),
                    provider="aws",
                    service="RDS",
                    resource_type="datastore/relational",
                    category="datastore",
                    name=dbid,
                    region=self.region,
                    account_id=self.account_id,
                    tags=self._get_tags_dict(db.get("TagList", [])),
                    merge_hints={
                        "arn": arn,
                        "resource_id": dbid,
                        "name_tag": dbid,
                        "endpoint": endpoint,
                    },
                    properties={
                        "db_instance_id": dbid,
                        "engine": db["Engine"],
                        "engine_version": db.get("EngineVersion"),
                        "status": db["DBInstanceStatus"],
                        "instance_class": db.get("DBInstanceClass"),
                        "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId"),
                        "endpoint": endpoint,
                        "port": db.get("Endpoint", {}).get("Port"),
                        "multi_az": db.get("MultiAZ"),
                        "allocated_storage": db.get("AllocatedStorage"),
                        "storage_type": db.get("StorageType"),
                        "db_subnet_group": db.get("DBSubnetGroup", {}).get("DBSubnetGroupName"),
                        "security_groups": [
                            sg.get("VpcSecurityGroupId")
                            for sg in db.get("VpcSecurityGroups", [])
                        ],
                    },
                    raw=db,
                ))

        # --- Aurora Clusters ---
        clusters_resp = rds.describe_db_clusters()
        for cluster in clusters_resp.get("DBClusters", []):
            cid = cluster["DBClusterIdentifier"]
            carn = cluster["DBClusterArn"]

            nodes.append(TopologyNode(
                uid=self._make_uid("rds", f"cluster/{cid}"),
                provider="aws",
                service="Aurora",
                resource_type="datastore/relational_cluster",
                category="datastore",
                name=f"{cid} (Cluster)",
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(cluster.get("TagList", [])),
                merge_hints={
                    "arn": carn,
                    "resource_id": cid,
                    "name_tag": cid,
                    "endpoint": cluster.get("Endpoint"),
                    "reader_endpoint": cluster.get("ReaderEndpoint"),
                },
                properties={
                    "cluster_id": cid,
                    "engine": cluster["Engine"],
                    "status": cluster["Status"],
                    "endpoint": cluster.get("Endpoint"),
                    "reader_endpoint": cluster.get("ReaderEndpoint"),
                    "member_count": len(cluster.get("DBClusterMembers", [])),
                    "vpc_id": cluster.get("DBSubnetGroup", {}).get("VpcId") if isinstance(cluster.get("DBSubnetGroup"), dict) else None,
                },
                raw=cluster,
            ))
        return nodes


class DynamoDBCollector(BaseCollector):
    """Discover DynamoDB tables."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "DynamoDB")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        dynamo = self._client("dynamodb")
        paginator = dynamo.get_paginator("list_tables")

        for page in paginator.paginate():
            for table_name in page.get("TableNames", []):
                table = dynamo.describe_table(TableName=table_name).get("Table", {})
                arn = table.get("TableArn", "")

                nodes.append(TopologyNode(
                    uid=self._make_uid("dynamodb", table_name),
                    provider="aws",
                    service="DynamoDB",
                    resource_type="datastore/nosql",
                    category="datastore",
                    name=table_name,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": table_name,
                        "name_tag": table_name,
                    },
                    properties={
                        "table_name": table_name,
                        "status": table.get("TableStatus"),
                        "item_count": table.get("ItemCount"),
                        "size_bytes": table.get("TableSizeBytes"),
                        "billing_mode": table.get("BillingModeSummary", {}).get("BillingMode"),
                    },
                    raw=table,
                ))
        return nodes


class RedshiftCollector(BaseCollector):
    """Discover Redshift clusters."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "Redshift")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        redshift = self._client("redshift")
        response = redshift.describe_clusters()

        for cluster in response.get("Clusters", []):
            cid = cluster["ClusterIdentifier"]
            arn = f"arn:aws:redshift:{self.region}:{self.account_id}:cluster:{cid}"
            endpoint = cluster.get("Endpoint", {}).get("Address")

            nodes.append(TopologyNode(
                uid=self._make_uid("redshift", cid),
                provider="aws",
                service="Redshift",
                resource_type="datastore/warehouse",
                category="datastore",
                name=cid,
                region=self.region,
                account_id=self.account_id,
                tags=self._get_tags_dict(cluster.get("Tags", [])),
                merge_hints={
                    "arn": arn,
                    "resource_id": cid,
                    "name_tag": cid,
                    "endpoint": endpoint,
                },
                properties={
                    "cluster_id": cid,
                    "node_type": cluster.get("NodeType"),
                    "number_of_nodes": cluster.get("NumberOfNodes"),
                    "status": cluster.get("ClusterStatus"),
                    "database_name": cluster.get("DBName"),
                    "endpoint": endpoint,
                    "vpc_id": cluster.get("VpcId"),
                },
                raw=cluster,
            ))
        return nodes
