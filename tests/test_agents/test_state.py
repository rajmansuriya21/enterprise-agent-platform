"""Tests for agent state and routing schema."""

from src.agents.state import AgentMetadata, AgentState, RouterDecision


class TestRouterDecision:
    """Tests for the RouterDecision schema."""

    def test_valid_rag_routing(self):
        decision = RouterDecision(
            next="rag_agent",
            reasoning="User asked about company policy",
            task_description="Find the leave policy",
        )
        assert decision.next == "rag_agent"
        assert decision.reasoning == "User asked about company policy"

    def test_valid_sql_routing(self):
        decision = RouterDecision(
            next="sql_agent",
            reasoning="User wants data analytics",
        )
        assert decision.next == "sql_agent"

    def test_valid_finish(self):
        decision = RouterDecision(
            next="FINISH",
            reasoning="Conversation complete",
        )
        assert decision.next == "FINISH"

    def test_default_task_description(self):
        decision = RouterDecision(
            next="api_agent",
            reasoning="External data needed",
        )
        assert decision.task_description == ""


class TestAgentMetadata:
    """Tests for the AgentMetadata model."""

    def test_creation(self):
        meta = AgentMetadata(
            agent_name="rag_agent",
            model_used="gpt-4o",
            latency_ms=342.5,
            tools_called=["vector_search"],
            success=True,
        )
        assert meta.agent_name == "rag_agent"
        assert meta.latency_ms == 342.5
        assert meta.tools_called == ["vector_search"]
        assert meta.success is True

    def test_defaults(self):
        meta = AgentMetadata(agent_name="test")
        assert meta.model_used == ""
        assert meta.tokens_used == 0
        assert meta.tools_called == []
        assert meta.success is True
        assert meta.error is None

    def test_serialization(self):
        meta = AgentMetadata(agent_name="test", latency_ms=100)
        data = meta.model_dump()
        assert data["agent_name"] == "test"
        assert data["latency_ms"] == 100
