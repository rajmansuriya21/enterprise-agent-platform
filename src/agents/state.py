"""
Shared state definitions for the LangGraph multi-agent system.

Defines the canonical AgentState that flows through the graph, and the
Router schema used by the Supervisor for structured output routing.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────
# Agent State — the shared state flowing through the LangGraph
# ──────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    """Canonical state schema for the multi-agent supervisor graph.

    Attributes:
        messages: Conversation history (appended via `operator.add`).
        next_agent: The next agent the supervisor wants to route to.
        context: Retrieved context from RAG / document extraction.
        tool_results: Accumulated results from tool executions.
        citations: Source document references for grounded generation.
        metadata: Auxiliary metadata (timing, token usage, etc.).
    """

    messages: Annotated[list[AnyMessage], operator.add]
    next_agent: str
    context: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    metadata: dict[str, Any]


# ──────────────────────────────────────────────────────────────
# Router Schema — structured output for the Supervisor
# ──────────────────────────────────────────────────────────────
AGENT_MEMBERS = ["rag_agent", "sql_agent", "api_agent", "doc_agent"]
AGENT_OPTIONS = Literal["rag_agent", "sql_agent", "api_agent", "doc_agent", "FINISH"]


class RouterDecision(BaseModel):
    """Structured output schema for the Supervisor's routing decision.

    The Supervisor LLM returns this schema to indicate which sub-agent
    should handle the current request, along with reasoning.
    """

    next: AGENT_OPTIONS = Field(
        description=(
            "The next agent to delegate to. Choose based on the user's intent:\n"
            "- 'rag_agent': For questions about documents, policies, knowledge base queries\n"
            "- 'sql_agent': For data queries, analytics, database questions (sales, employees, etc.)\n"
            "- 'api_agent': For real-time external data (weather, stocks, news, web search)\n"
            "- 'doc_agent': For parsing/extracting info from uploaded documents (PDF, DOCX)\n"
            "- 'FINISH': When the conversation is complete and no further action is needed"
        )
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen (1-2 sentences)."
    )
    task_description: str = Field(
        default="",
        description="Specific task instruction for the selected sub-agent.",
    )


# ──────────────────────────────────────────────────────────────
# Agent Metadata — for tracking and observability
# ──────────────────────────────────────────────────────────────
class AgentMetadata(BaseModel):
    """Metadata tracked for each agent invocation."""

    agent_name: str
    model_used: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    tools_called: list[str] = Field(default_factory=list)
    success: bool = True
    error: str | None = None
