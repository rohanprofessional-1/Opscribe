"""
Integration service collectors: SQS, SNS, EventBridge, APIGateway.
"""

from __future__ import annotations

from apps.api.ingestors.aws.schema import TopologyNode
from apps.api.ingestors.aws.collectors.base import BaseCollector


class SQSCollector(BaseCollector):
    """Discover SQS queues."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "SQS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        sqs = self._client("sqs")
        paginator = sqs.get_paginator("list_queues")

        for page in paginator.paginate():
            for queue_url in page.get("QueueUrls", []):
                qname = queue_url.split("/")[-1]
                arn = f"arn:aws:sqs:{self.region}:{self.account_id}:{qname}"

                nodes.append(TopologyNode(
                    uid=self._make_uid("sqs", qname),
                    provider="aws",
                    service="SQS",
                    resource_type="integration/queue",
                    category="integration",
                    name=qname,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": arn,
                        "resource_id": qname,
                        "name_tag": qname,
                        "queue_url": queue_url,
                    },
                    properties={
                        "queue_name": qname,
                        "queue_url": queue_url,
                    },
                    raw={"queue_url": queue_url, "queue_name": qname},
                ))
        return nodes


class SNSCollector(BaseCollector):
    """Discover SNS topics."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "SNS")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        sns = self._client("sns")
        paginator = sns.get_paginator("list_topics")

        for page in paginator.paginate():
            for topic in page.get("Topics", []):
                topic_arn = topic["TopicArn"]
                tname = topic_arn.split(":")[-1]

                nodes.append(TopologyNode(
                    uid=self._make_uid("sns", tname),
                    provider="aws",
                    service="SNS",
                    resource_type="integration/topic",
                    category="integration",
                    name=tname,
                    region=self.region,
                    account_id=self.account_id,
                    tags={},
                    merge_hints={
                        "arn": topic_arn,
                        "resource_id": tname,
                        "name_tag": tname,
                    },
                    properties={
                        "topic_name": tname,
                        "topic_arn": topic_arn,
                    },
                    raw=topic,
                ))
        return nodes


class EventBridgeCollector(BaseCollector):
    """Discover EventBridge rules."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "EventBridge")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        events = self._client("events")
        response = events.list_rules()

        for rule in response.get("Rules", []):
            rname = rule["Name"]
            arn = rule.get("Arn", f"arn:aws:events:{self.region}:{self.account_id}:rule/{rname}")

            nodes.append(TopologyNode(
                uid=self._make_uid("events", f"rule/{rname}"),
                provider="aws",
                service="EventBridge",
                resource_type="integration/event_rule",
                category="integration",
                name=rname,
                region=self.region,
                account_id=self.account_id,
                tags={},
                merge_hints={
                    "arn": arn,
                    "resource_id": rname,
                    "name_tag": rname,
                },
                properties={
                    "rule_name": rname,
                    "state": rule.get("State"),
                    "event_pattern": rule.get("EventPattern"),
                    "schedule_expression": rule.get("ScheduleExpression"),
                    "event_bus_name": rule.get("EventBusName"),
                },
                raw=rule,
            ))
        return nodes


class APIGatewayCollector(BaseCollector):
    """Discover API Gateway REST APIs."""

    def collect(self) -> list[TopologyNode]:
        return self._safe_collect(self._collect, "APIGateway")

    def _collect(self) -> list[TopologyNode]:
        nodes: list[TopologyNode] = []
        apigw = self._client("apigateway")
        response = apigw.get_rest_apis()

        for api in response.get("items", []):
            aid = api["id"]
            aname = api.get("name", aid)
            arn = f"arn:aws:apigateway:{self.region}::/restapis/{aid}"

            nodes.append(TopologyNode(
                uid=self._make_uid("apigateway", aid),
                provider="aws",
                service="APIGateway",
                resource_type="integration/api",
                category="integration",
                name=aname,
                region=self.region,
                account_id=self.account_id,
                tags=api.get("tags", {}),
                merge_hints={
                    "arn": arn,
                    "resource_id": aid,
                    "name_tag": aname,
                },
                properties={
                    "api_id": aid,
                    "api_name": aname,
                    "protocol": "REST",
                    "description": api.get("description"),
                    "created_date": api.get("createdDate").isoformat() if api.get("createdDate") else None,
                },
                raw=api,
            ))
        return nodes
