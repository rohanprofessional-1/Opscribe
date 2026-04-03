"""
Tests for the LangChain graph traversal tools.

Verifies that the tool factory returns correctly configured BaseTool instances,
that each tool delegates to GraphTraversalService properly, and that edge cases
(missing nodes, empty results) are handled gracefully without erroring.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID


# ── Helpers ────────────────────────────────────────────────────────────

def make_mock_svc(
    find_node_result=None,
    find_nodes_fuzzy_result=None,
    get_neighbors_result=None,
    get_dependency_chain_result=None,
    get_impact_radius_result=None,
    find_paths_result=None,
):
    """Build a mock GraphTraversalService with configurable return values."""
    svc = MagicMock()
    svc.find_node.return_value = find_node_result
    svc.find_nodes_fuzzy.return_value = find_nodes_fuzzy_result or []
    svc.get_neighbors.return_value = get_neighbors_result or []
    svc.get_dependency_chain.return_value = get_dependency_chain_result or {
        "root": {"name": "Root"}, "nodes": [], "total": 0
    }
    svc.get_impact_radius.return_value = get_impact_radius_result or {
        "root": {"name": "Root"}, "nodes": [], "total": 0
    }
    svc.find_paths.return_value = find_paths_result or []
    return svc


def get_tools_with_mock_svc(svc, graph_id=None):
    """
    Import get_graph_traversal_tools and patch GraphTraversalService
    to inject the mock svc. Returns a dict of tool_name -> tool.
    
    GraphTraversalService is imported inside the function on-demand, so we
    must patch it in its defining module (not in graph_tools).
    """
    gid = graph_id or uuid4()
    session = MagicMock()

    with patch(
        "apps.api.ai_infrastructure.graph.graph_traversal.GraphTraversalService",
        return_value=svc,
    ):
        from apps.api.ai_infrastructure.agent.tools import graph_tools as gt_module
        # Reload to pick up the newly patched module
        import importlib
        importlib.reload(gt_module)
        tools = gt_module.get_graph_traversal_tools(session, gid)

    return {t.name: t for t in tools}


# ── Test: Tool Factory ─────────────────────────────────────────────────

class TestGetGraphTraversalTools:
    def test_returns_five_tools(self):
        svc = make_mock_svc()
        tools = get_tools_with_mock_svc(svc)
        assert len(tools) == 5

    def test_tool_names_are_correct(self):
        svc = make_mock_svc()
        tools = get_tools_with_mock_svc(svc)
        expected = {
            "find_node_by_name",
            "get_neighbors",
            "get_dependency_chain",
            "get_impact_radius",
            "find_paths_between",
        }
        assert set(tools.keys()) == expected

    def test_all_tools_have_descriptions(self):
        svc = make_mock_svc()
        tools = get_tools_with_mock_svc(svc)
        for name, tool in tools.items():
            assert tool.description, f"Tool '{name}' has no description"


# ── Test: find_node_by_name ────────────────────────────────────────────

class TestFindNodeByName:
    def test_returns_node_details_on_exact_match(self):
        node = {
            "id": str(uuid4()), "key": "api-gw", "name": "API Gateway",
            "category": "Service", "properties": {"region": "us-east-1"},
        }
        svc = make_mock_svc(find_node_result=node)
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_node_by_name"].run("API Gateway")
        assert "API Gateway" in result
        assert "us-east-1" in result

    def test_returns_not_found_when_no_match(self):
        svc = make_mock_svc(find_node_result=None, find_nodes_fuzzy_result=[])
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_node_by_name"].run("Unknown Service")
        assert "No node found" in result

    def test_returns_single_fuzzy_match(self):
        node = {
            "id": str(uuid4()), "key": "redis", "name": "Redis Cache",
            "category": "Cache", "properties": {},
        }
        svc = make_mock_svc(find_node_result=None, find_nodes_fuzzy_result=[node])
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_node_by_name"].run("redis")
        assert "Redis Cache" in result

    def test_returns_disambiguation_on_multiple_fuzzy_matches(self):
        matches = [
            {"name": "Redis Cache", "id": str(uuid4()), "key": "redis-1", "category": "Cache", "properties": {}},
            {"name": "Redis Session", "id": str(uuid4()), "key": "redis-2", "category": "Cache", "properties": {}},
        ]
        svc = make_mock_svc(find_node_result=None, find_nodes_fuzzy_result=matches)
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_node_by_name"].run("redis")
        assert "Multiple nodes match" in result
        assert "Redis Cache" in result
        assert "Redis Session" in result


# ── Test: get_neighbors ────────────────────────────────────────────────

class TestGetNeighbors:
    def test_returns_neighbor_list(self):
        node = {"id": str(uuid4()), "key": "api-gw", "name": "API Gateway",
                "category": "Service", "properties": {}}
        neighbors = [
            {"name": "Lambda", "category": "Compute", "relationship": "calls"},
            {"name": "RDS", "category": "Database", "relationship": "stores_in"},
        ]
        svc = make_mock_svc(find_node_result=node, get_neighbors_result=neighbors)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_neighbors"].run("API Gateway")
        assert "Lambda" in result
        assert "RDS" in result

    def test_returns_no_neighbors_message(self):
        node = {"id": str(uuid4()), "key": "leaf", "name": "Leaf Node",
                "category": "Misc", "properties": {}}
        svc = make_mock_svc(find_node_result=node, get_neighbors_result=[])
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_neighbors"].run("Leaf Node")
        assert "no" in result.lower()

    def test_returns_not_found_for_missing_node(self):
        svc = make_mock_svc(find_node_result=None)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_neighbors"].run("Nonexistent")
        assert "not found" in result


# ── Test: get_dependency_chain ─────────────────────────────────────────

class TestGetDependencyChain:
    def test_returns_dependency_tree(self):
        node = {"id": str(uuid4()), "key": "sf", "name": "Serverless Function",
                "category": "Compute", "properties": {}}
        chain_result = {
            "root": {"name": "Serverless Function"},
            "nodes": [
                {"name": "Cache DB", "category": "Database", "depth": 1},
                {"name": "S3 Bucket", "category": "Storage", "depth": 2},
            ],
            "total": 2,
        }
        svc = make_mock_svc(find_node_result=node, get_dependency_chain_result=chain_result)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_dependency_chain"].run("Serverless Function")
        assert "Cache DB" in result
        assert "S3 Bucket" in result

    def test_returns_no_dependencies_message(self):
        node = {"id": str(uuid4()), "key": "leaf", "name": "Leaf",
                "category": "Misc", "properties": {}}
        chain_result = {"root": {"name": "Leaf"}, "nodes": [], "total": 0}
        svc = make_mock_svc(find_node_result=node, get_dependency_chain_result=chain_result)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_dependency_chain"].run("Leaf")
        assert "no" in result.lower()


# ── Test: get_impact_radius ────────────────────────────────────────────

class TestGetImpactRadius:
    def test_returns_impact_nodes(self):
        node = {"id": str(uuid4()), "key": "db", "name": "Primary DB",
                "category": "Database", "properties": {}}
        impact = {
            "root": {"name": "Primary DB"},
            "nodes": [
                {"name": "API Gateway", "category": "Service", "depth": 1},
                {"name": "Frontend", "category": "Web", "depth": 2},
            ],
            "total": 2,
        }
        svc = make_mock_svc(find_node_result=node, get_impact_radius_result=impact)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_impact_radius"].run("Primary DB")
        assert "API Gateway" in result
        assert "Frontend" in result

    def test_returns_no_impact_message(self):
        node = {"id": str(uuid4()), "key": "isolated", "name": "Isolated",
                "category": "Misc", "properties": {}}
        impact = {"root": {"name": "Isolated"}, "nodes": [], "total": 0}
        svc = make_mock_svc(find_node_result=node, get_impact_radius_result=impact)
        tools = get_tools_with_mock_svc(svc)
        result = tools["get_impact_radius"].run("Isolated")
        assert "Nothing depends on" in result


# ── Test: find_paths_between ───────────────────────────────────────────

class TestFindPathsBetween:
    def test_returns_path_between_nodes(self):
        source = {"id": str(uuid4()), "key": "sf", "name": "Lambda",
                  "category": "Compute", "properties": {}}
        target = {"id": str(uuid4()), "key": "db", "name": "RDS",
                  "category": "Database", "properties": {}}

        svc = make_mock_svc(find_node_result=None)
        svc.find_node.side_effect = [source, target]
        svc.find_paths.return_value = [
            [{"name": "Lambda"}, {"name": "API Gateway"}, {"name": "RDS"}]
        ]
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_paths_between"].run({"source_name": "Lambda", "target_name": "RDS"})
        assert "Lambda" in result
        assert "RDS" in result

    def test_returns_no_paths_message(self):
        source = {"id": str(uuid4()), "key": "a", "name": "NodeA",
                  "category": "Service", "properties": {}}
        target = {"id": str(uuid4()), "key": "b", "name": "NodeB",
                  "category": "Service", "properties": {}}

        svc = make_mock_svc(find_node_result=None)
        svc.find_node.side_effect = [source, target]
        svc.find_paths.return_value = []
        tools = get_tools_with_mock_svc(svc)
        result = tools["find_paths_between"].run({"source_name": "NodeA", "target_name": "NodeB"})
        assert "No paths found" in result
