"""
Tests for GraphTraversalService.

Uses mock SQLModel sessions to verify traversal logic without a database.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

from apps.api.ai_infrastructure.graph.graph_traversal import GraphTraversalService


# ── Fixtures ──────────────────────────────────────────────────────────

def make_node(key: str, display_name: str, node_id: UUID = None):
    """Create a mock Node object."""
    node = MagicMock()
    node.id = node_id or uuid4()
    node.key = key
    node.display_name = display_name
    node.properties = {"category": "Service", "label": display_name}
    node.node_type = MagicMock()
    node.node_type.name = "Infrastructure"
    node.graph_id = uuid4()
    return node


def make_edge(from_id: UUID, to_id: UUID, edge_id: UUID = None):
    """Create a mock Edge object."""
    edge = MagicMock()
    edge.id = edge_id or uuid4()
    edge.from_node_id = from_id
    edge.to_node_id = to_id
    edge.edge_type_id = uuid4()
    edge.edge_type = MagicMock()
    edge.edge_type.name = "connects"
    edge.properties = {}
    edge.graph_id = uuid4()
    return edge


# ── Test: _node_to_dict ──────────────────────────────────────────────

class TestNodeToDict:
    def test_filters_ui_properties(self):
        node = make_node("api-gw", "API Gateway")
        node.properties = {
            "category": "Service",
            "label": "API Gateway",
            "position": {"x": 100, "y": 200},
            "x": 100,
            "y": 200,
            "selected": True,
            "region": "us-east-1",
        }
        result = GraphTraversalService._node_to_dict(node)

        assert result["name"] == "API Gateway"
        assert result["key"] == "api-gw"
        assert "position" not in result["properties"]
        assert "x" not in result["properties"]
        assert "selected" not in result["properties"]
        assert result["properties"]["region"] == "us-east-1"

    def test_uses_key_as_fallback_name(self):
        node = make_node("redis-cache", None)
        node.display_name = None
        result = GraphTraversalService._node_to_dict(node)
        assert result["name"] == "redis-cache"


# ── Test: _edge_to_dict ──────────────────────────────────────────────

class TestEdgeToDict:
    def test_serializes_edge(self):
        from_id, to_id = uuid4(), uuid4()
        edge = make_edge(from_id, to_id)
        result = GraphTraversalService._edge_to_dict(edge)

        assert result["from_node_id"] == str(from_id)
        assert result["to_node_id"] == str(to_id)
        assert "id" in result


# ── Test: WorkflowSpec ────────────────────────────────────────────────

class TestWorkflowSpec:
    def test_defaults(self):
        from apps.api.ai_infrastructure.workflows.workflow_spec import WorkflowSpec

        spec = WorkflowSpec(
            action="provision",
            tool="terraform",
            target_nodes=["redis-main"],
        )
        assert spec.requires_approval is True
        assert spec.dry_run is True
        assert spec.parameters == {}

    def test_all_fields(self):
        from apps.api.ai_infrastructure.workflows.workflow_spec import WorkflowSpec

        spec = WorkflowSpec(
            action="scale",
            tool="pulumi",
            target_nodes=["ecs-api", "ecs-worker"],
            parameters={"desired_count": 5},
            requires_approval=False,
            dry_run=False,
            description="Scale ECS services for traffic spike",
        )
        assert spec.action == "scale"
        assert spec.tool == "pulumi"
        assert len(spec.target_nodes) == 2
        assert spec.description == "Scale ECS services for traffic spike"


# ── Test: QueryRouter ─────────────────────────────────────────────────

class TestQueryRouter:
    def test_classifies_rag_intent(self):
        from apps.api.ai_infrastructure.router.query_router import QueryRouter

        llm = MagicMock()
        llm_response = MagicMock()
        llm_response.content = '{"intent": "rag"}'

        router = QueryRouter(llm)
        router.chain = MagicMock()
        router.chain.invoke = MagicMock(return_value=llm_response)

        assert router.classify("What is the API gateway?") == "rag"

    def test_classifies_traversal_intent(self):
        from apps.api.ai_infrastructure.router.query_router import QueryRouter

        llm = MagicMock()
        llm_response = MagicMock()
        llm_response.content = '{"intent": "traversal"}'

        router = QueryRouter(llm)
        router.chain = MagicMock()
        router.chain.invoke = MagicMock(return_value=llm_response)

        assert router.classify("What depends on the database?") == "traversal"

    def test_falls_back_to_rag_on_error(self):
        from apps.api.ai_infrastructure.router.query_router import QueryRouter

        llm = MagicMock()

        router = QueryRouter(llm)
        router.chain = MagicMock()
        router.chain.invoke = MagicMock(side_effect=Exception("LLM failed"))

        assert router.classify("broken query") == "rag"

    def test_falls_back_to_rag_on_bad_json(self):
        from apps.api.ai_infrastructure.router.query_router import QueryRouter

        llm = MagicMock()
        llm_response = MagicMock()
        llm_response.content = "not valid json!"

        router = QueryRouter(llm)
        router.chain = MagicMock()
        router.chain.invoke = MagicMock(return_value=llm_response)

        assert router.classify("broken query") == "rag"
