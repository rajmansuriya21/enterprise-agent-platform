"""
Supervisor Agent — LangGraph-based multi-agent orchestrator.

The Supervisor uses GPT-4 / Qwen with structured output to intelligently
route user requests to specialized sub-agents (RAG, SQL, API, Doc Extraction).
It aggregates responses, manages conversation state, and ensures citation-grounded output.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from src.agents.state import (
    AGENT_MEMBERS,
    AgentMetadata,
    AgentState,
    RouterDecision,
)
from src.config import get_settings
from src.utils.prompts import SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Supervisor Node
# ──────────────────────────────────────────────────────────────
def create_supervisor_node(llm: Any):
    """Create the supervisor node function with the given LLM.

    The supervisor analyzes the conversation and decides which sub-agent
    to invoke next using structured output (RouterDecision schema).
    """

    def supervisor_node(
        state: AgentState,
    ) -> Command[Literal["rag_agent", "sql_agent", "api_agent", "doc_agent", "__end__"]]:
        """Supervisor node: routes to the appropriate sub-agent or finishes."""
        start_time = time.time()

        # Build message list with system prompt
        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            *state["messages"],
        ]

        # Get structured routing decision from LLM
        structured_llm = llm.with_structured_output(RouterDecision)

        try:
            decision: RouterDecision = structured_llm.invoke(messages)
            logger.info(
                "Supervisor routing decision",
                extra={
                    "next_agent": decision.next,
                    "reasoning": decision.reasoning,
                },
            )
        except Exception as e:
            logger.error(f"Supervisor routing failed: {e}")
            # Default to FINISH on routing failure
            decision = RouterDecision(
                next="FINISH",
                reasoning=f"Routing failed with error: {str(e)}",
                task_description="",
            )

        # Determine target
        goto = decision.next
        if goto == "FINISH":
            goto_target = "__end__"
        else:
            goto_target = goto

        # Track metadata
        latency_ms = (time.time() - start_time) * 1000
        metadata = state.get("metadata", {})
        routing_history = metadata.get("routing_history", [])
        routing_history.append(
            AgentMetadata(
                agent_name="supervisor",
                model_used=get_settings().llm_model,
                latency_ms=latency_ms,
                success=True,
            ).model_dump()
        )
        metadata["routing_history"] = routing_history
        metadata["last_reasoning"] = decision.reasoning
        metadata["last_task"] = decision.task_description

        # Add supervisor's reasoning as a message for context
        update: dict[str, Any] = {
            "messages": [
                AIMessage(
                    content=f"[Supervisor → {decision.next}] {decision.reasoning}",
                    name="supervisor",
                )
            ],
            "next_agent": decision.next,
            "metadata": metadata,
        }

        return Command(goto=goto_target, update=update)

    return supervisor_node


# ──────────────────────────────────────────────────────────────
# Response Aggregator Node
# ──────────────────────────────────────────────────────────────
def create_response_aggregator(llm: Any):
    """Create the response aggregator that formats the final answer
    with citations and routes back to supervisor for continuation check."""

    def response_aggregator(state: AgentState) -> Command[Literal["supervisor"]]:
        """Aggregate sub-agent results and return to supervisor for next decision."""
        # The sub-agent has already added its response to messages.
        # Route back to supervisor to decide if more work is needed.
        return Command(goto="supervisor")

    return response_aggregator


# ──────────────────────────────────────────────────────────────
# Graph Builder
# ──────────────────────────────────────────────────────────────
def build_agent_graph(
    llm: Any,
    rag_agent_fn: Any,
    sql_agent_fn: Any,
    api_agent_fn: Any,
    doc_agent_fn: Any,
    checkpointer: Any | None = None,
) -> StateGraph:
    """Build the complete multi-agent LangGraph.

    Architecture:
        User → Supervisor → [RAG | SQL | API | Doc] → Aggregator → Supervisor → ... → END

    Args:
        llm: The LLM instance for the supervisor.
        rag_agent_fn: RAG sub-agent node function.
        sql_agent_fn: SQL sub-agent node function.
        api_agent_fn: API sub-agent node function.
        doc_agent_fn: Document extraction sub-agent node function.
        checkpointer: Optional checkpointer for state persistence.

    Returns:
        Compiled LangGraph ready for invocation.
    """
    # Create node functions
    supervisor = create_supervisor_node(llm)
    aggregator = create_response_aggregator(llm)

    # Build the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("rag_agent", rag_agent_fn)
    graph.add_node("sql_agent", sql_agent_fn)
    graph.add_node("api_agent", api_agent_fn)
    graph.add_node("doc_agent", doc_agent_fn)
    graph.add_node("aggregator", aggregator)

    # Add edges: each sub-agent → aggregator → supervisor
    for member in AGENT_MEMBERS:
        graph.add_edge(member, "aggregator")

    # Entry point
    graph.set_entry_point("supervisor")

    # Use checkpointer for stateful conversations
    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Multi-agent graph compiled successfully")
    return compiled


# ──────────────────────────────────────────────────────────────
# Convenience: create the full platform graph
# ──────────────────────────────────────────────────────────────
def create_platform_graph(
    llm: Any | None = None,
    vector_store: Any | None = None,
    db_service: Any | None = None,
    cache_service: Any | None = None,
) -> Any:
    """Create the full enterprise platform graph with all sub-agents wired up.

    This is the main entry point for constructing the agent system.
    """
    from src.agents.rag_agent import create_rag_agent_node
    from src.agents.sql_agent import create_sql_agent_node
    from src.agents.api_agent import create_api_agent_node
    from src.agents.doc_agent import create_doc_agent_node
    from src.services.llm_provider import get_llm

    if llm is None:
        llm = get_llm()

    # Create sub-agent nodes
    rag_node = create_rag_agent_node(llm=llm, vector_store=vector_store)
    sql_node = create_sql_agent_node(llm=llm, db_service=db_service)
    api_node = create_api_agent_node(llm=llm)
    doc_node = create_doc_agent_node(llm=llm, vector_store=vector_store)

    # Build and return compiled graph
    return build_agent_graph(
        llm=llm,
        rag_agent_fn=rag_node,
        sql_agent_fn=sql_node,
        api_agent_fn=api_node,
        doc_agent_fn=doc_node,
    )


# ──────────────────────────────────────────────────────────────
# Invocation helpers
# ──────────────────────────────────────────────────────────────
async def invoke_agent(
    graph: Any,
    user_message: str,
    thread_id: str = "default",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke the multi-agent graph with a user message.

    Args:
        graph: Compiled LangGraph.
        user_message: The user's input message.
        thread_id: Conversation thread ID for state persistence.
        metadata: Optional metadata to pass through.

    Returns:
        Dictionary with response, citations, metadata, and routing info.
    """
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "next_agent": "",
        "context": [],
        "tool_results": [],
        "citations": [],
        "metadata": metadata or {},
    }

    # Invoke the graph
    result = await graph.ainvoke(initial_state, config=config)

    # Extract the final response (last AI message that isn't from supervisor)
    final_response = ""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and getattr(msg, "name", "") != "supervisor":
            final_response = msg.content
            break

    return {
        "response": final_response,
        "citations": result.get("citations", []),
        "metadata": result.get("metadata", {}),
        "messages": result.get("messages", []),
    }


async def stream_agent(
    graph: Any,
    user_message: str,
    thread_id: str = "default",
    metadata: dict[str, Any] | None = None,
):
    """Stream the multi-agent graph execution, yielding events as they occur.

    Yields:
        Dict events with agent routing info, tool calls, and response chunks.
    """
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "next_agent": "",
        "context": [],
        "tool_results": [],
        "citations": [],
        "metadata": metadata or {},
    }

    async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            yield {
                "node": node_name,
                "output": node_output,
            }
