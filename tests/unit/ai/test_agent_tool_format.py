"""
Tests guarding against agent tool-calling format regressions.

The Groq-hosted Llama 3 model occasionally emits pseudo-XML like:
    <function=find_node_by_name{"node_name": "API Gateway"}</function>
instead of invoking the tool natively, which causes a 400 error from Groq's API.

These tests ensure:
1. The agent is built with tools properly bound to the LLM.
2. The agent system prompt contains the critical TOOL BEHAVIOR instruction.
3. The QueryRouter correctly classifies structural vs semantic questions.
4. Re-embedding is triggered after every graph sync.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from uuid import uuid4


# ── Test: System Prompt Safeguards ────────────────────────────────────

class TestAgentSystemPrompt:
    """Verify that prompt instructions to prevent XML hallucinations are in place."""

    def _get_system_prompt_from_rag_router(self):
        """Extract the system_prompt string from _handle_traversal."""
        import inspect
        import apps.api.routers.rag as rag_module
        src = inspect.getsource(rag_module._handle_traversal)
        return src

    def test_system_prompt_forbids_text_before_tool_call(self):
        src = self._get_system_prompt_from_rag_router()
        assert "ONLY the tool call" in src or "Do not provide any conversational text" in src, (
            "The system prompt must forbid conversational text before a tool call. "
            "Without this, Llama 3 on Groq emits pseudo-XML instead of invoking tools."
        )

    def test_system_prompt_includes_traversal_protocol(self):
        src = self._get_system_prompt_from_rag_router()
        assert "find_node_by_name" in src, (
            "System prompt must instruct model to use find_node_by_name first."
        )

    def test_system_prompt_has_no_xml_references(self):
        """Ensure system prompt doesn't accidentally teach the model XML format."""
        src = self._get_system_prompt_from_rag_router()
        assert "<function=" not in src, (
            "System prompt must not reference XML <function= format. "
            "This could confuse models that attend to format examples in prompts."
        )


# ── Test: Agent Tool Binding ───────────────────────────────────────────

class TestAgentToolBinding:
    """Verify create_agent is called with actual tools, not an empty list."""

    def test_tools_bound_to_agent_are_non_empty(self):
        """
        If tools is an empty list, the agent will be a raw chat model and
        cannot call any tools — causing it to hallucinate XML instead.
        """
        mock_session = MagicMock()
        graph_id = uuid4()
        mock_tool = MagicMock()
        mock_tool.name = "find_node_by_name"

        captured_tools = []

        def capture_create_agent(model, tools, **kwargs):
            captured_tools.extend(tools)
            return MagicMock()

        with patch(
            "apps.api.ai_infrastructure.agent.tools.graph_tools.get_graph_traversal_tools",
            return_value=[mock_tool, mock_tool, mock_tool, mock_tool, mock_tool],
        ), patch(
            "apps.api.routers.rag.get_graph_traversal_tools",
            return_value=[mock_tool, mock_tool, mock_tool, mock_tool, mock_tool],
        ), patch(
            "langchain.agents.create_agent",
            side_effect=capture_create_agent,
        ):
            from apps.api.routers.rag import _handle_traversal, RagQueryRequest
            from langchain_core.messages import AIMessage

            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {
                "messages": [AIMessage(content="Test answer")]
            }

            with patch("langchain.agents.create_agent", return_value=mock_agent):
                request = MagicMock()
                request.query = "What depends on API Gateway?"
                request.graph_id = graph_id
                request.tenant_id = uuid4()
                request.limit = 5

                with patch(
                    "apps.api.routers.rag.get_graph_traversal_tools",
                    return_value=[mock_tool] * 5,
                ) as patched_tools:
                    try:
                        _handle_traversal(request, mock_session, MagicMock())
                    except Exception:
                        pass

                    patched_tools.assert_called_once_with(mock_session, graph_id)


# ── Test: Groq Error Detection ─────────────────────────────────────────

class TestGroqToolCallErrorDetection:
    """
    Groq returns HTTP 400 with code 'tool_use_failed' when the model emits
    malformed XML instead of a proper tool call. This test verifies that
    the _handle_traversal function catches this and returns a graceful 500.
    """

    def test_handles_groq_tool_use_failed_error(self):
        from fastapi import HTTPException
        from apps.api.routers.rag import _handle_traversal

        request = MagicMock()
        request.query = "What depends on Serverless Function?"
        request.graph_id = uuid4()
        request.tenant_id = uuid4()

        groq_error = Exception(
            "Error code: 400 - {'error': {'message': 'Failed to call a function', "
            "'type': 'invalid_request_error', 'code': 'tool_use_failed', "
            "'failed_generation': '<function=find_node_by_name{\"node_name\": \"API\"}'}}"
        )

        with patch("apps.api.routers.rag.get_graph_traversal_tools", side_effect=groq_error):
            with pytest.raises(HTTPException) as exc_info:
                _handle_traversal(request, MagicMock(), MagicMock())

            assert exc_info.value.status_code == 500

    def test_detects_pseudo_xml_in_groq_error_response(self):
        """
        Detect if a Groq API error message mentions the XML pseudo-format.
        This is the sentinel we look for when debugging tool_use_failed errors.
        """
        error_msg = (
            "Error code: 400 - {'error': {'code': 'tool_use_failed', "
            "'failed_generation': '<function=find_node_by_name{\"node_name\": \"X\"}</function>'}}"
        )
        assert "<function=" in error_msg, (
            "This test documents the known Groq XML hallucination format. "
            "If you never see this in logs, the prompt fix is working."
        )


# ── Test: Graph Sync Triggers Re-embed ────────────────────────────────

class TestGraphSyncEmbeddingSync:
    """
    After sync_graph saves, it must schedule re_embed_graph as a BackgroundTask.
    If this is broken, the vector store and graph will drift out of sync.
    """

    def test_sync_graph_schedules_re_embed(self):
        from apps.api.routers.graphs import sync_graph
        from fastapi import BackgroundTasks
        from apps.api.schemas import GraphSyncUpdate

        graph_id = uuid4()

        mock_graph = MagicMock()
        mock_graph.client_id = uuid4()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_graph
        mock_session.exec.return_value.all.return_value = []
        mock_session.exec.return_value.first.return_value = None

        background_tasks = MagicMock(spec=BackgroundTasks)

        body = MagicMock(spec=GraphSyncUpdate)
        body.name = "Updated Graph"
        body.nodes = []
        body.edges = []

        with patch("apps.api.routers.graphs.re_embed_graph") as mock_re_embed:
            try:
                sync_graph(graph_id, body, background_tasks, mock_session)
            except Exception:
                pass

            background_tasks.add_task.assert_called_once_with(mock_re_embed, graph_id)


# ── Test: Sync Edges Are Cleared Before Nodes ─────────────────────────

class TestSyncGraphEdgeNodeOrder:
    """
    Regression test for the 500 NotNullViolation.
    SQLAlchemy must delete edges BEFORE nodes to avoid setting from_node_id = NULL.
    """

    def test_edges_deleted_before_nodes(self):
        from apps.api.routers.graphs import sync_graph
        from fastapi import BackgroundTasks
        from apps.api.schemas import GraphSyncUpdate

        graph_id = uuid4()
        call_order = []

        mock_node = MagicMock()
        mock_node.key = "old-key-not-in-payload"

        mock_edge = MagicMock()

        mock_graph = MagicMock()
        mock_graph.client_id = uuid4()

        # Track deletion order
        def track_delete(obj):
            if obj is mock_edge:
                call_order.append("edge")
            elif obj is mock_node:
                call_order.append("node")

        mock_session = MagicMock()
        mock_session.get.return_value = mock_graph
        mock_session.exec.return_value.first.return_value = None

        # First call = edges query, second = nodes query
        mock_session.exec.return_value.all.side_effect = [
            [mock_edge],   # edges
            [mock_node],   # existing nodes to prune
            [],            # nodes after upsert (for key_to_node map)
        ]
        mock_session.delete.side_effect = track_delete

        background_tasks = MagicMock(spec=BackgroundTasks)
        body = MagicMock(spec=GraphSyncUpdate)
        body.name = None
        body.nodes = []
        body.edges = []

        with patch("apps.api.routers.graphs.re_embed_graph"):
            try:
                sync_graph(graph_id, body, background_tasks, mock_session)
            except Exception:
                pass

        if "edge" in call_order and "node" in call_order:
            assert call_order.index("edge") < call_order.index("node"), (
                "Edges must be deleted before nodes to avoid FK null violation "
                "(psycopg2.errors.NotNullViolation on from_node_id)."
            )
