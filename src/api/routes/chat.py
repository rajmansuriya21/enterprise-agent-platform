"""
Chat Routes — Synchronous and streaming chat endpoints.

Handles user interactions with the multi-agent system via REST and WebSocket.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """Chat request body."""

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Conversation thread ID for state persistence",
    )
    model: str | None = Field(default=None, description="LLM model override")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class Citation(BaseModel):
    """A source citation."""

    source_id: int
    file: str
    score: float
    content_preview: str = ""


class AgentTrace(BaseModel):
    """Trace information for a single agent invocation."""

    agent_name: str
    model_used: str = ""
    latency_ms: float = 0.0
    tools_called: list[str] = []
    success: bool = True


class ChatResponse(BaseModel):
    """Chat response body."""

    response: str
    thread_id: str
    citations: list[Citation] = []
    agent_traces: list[AgentTrace] = []
    routing_reasoning: str = ""
    total_latency_ms: float = 0.0


# ──────────────────────────────────────────────────────────────
# Synchronous Chat Endpoint
# ──────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message through the multi-agent system.

    The message is analyzed by the Supervisor agent which routes it to
    the appropriate sub-agent (RAG, SQL, API, or Document Extraction).
    """
    import time

    start_time = time.time()

    try:
        from src.agents.supervisor import create_platform_graph, invoke_agent

        # Create or retrieve the agent graph
        graph = create_platform_graph()

        # Invoke the multi-agent system
        result = await invoke_agent(
            graph=graph,
            user_message=request.message,
            thread_id=request.thread_id,
        )

        # Extract metadata
        metadata = result.get("metadata", {})
        routing_history = metadata.get("routing_history", [])

        # Build agent traces
        traces = [
            AgentTrace(**trace)
            for trace in routing_history
            if isinstance(trace, dict)
        ]

        # Build citations
        citations = [
            Citation(**cite)
            for cite in result.get("citations", [])
            if isinstance(cite, dict)
        ]

        total_latency = (time.time() - start_time) * 1000

        return ChatResponse(
            response=result.get("response", "No response generated."),
            thread_id=request.thread_id,
            citations=citations,
            agent_traces=traces,
            routing_reasoning=metadata.get("last_reasoning", ""),
            total_latency_ms=round(total_latency, 2),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        total_latency = (time.time() - start_time) * 1000
        return ChatResponse(
            response=f"I apologize, but I encountered an error processing your request: {str(e)}",
            thread_id=request.thread_id,
            total_latency_ms=round(total_latency, 2),
        )


# ──────────────────────────────────────────────────────────────
# WebSocket Streaming Endpoint
# ──────────────────────────────────────────────────────────────
@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Stream chat responses via WebSocket.

    Protocol:
    - Client sends: {"message": "...", "thread_id": "..."}
    - Server streams: {"type": "routing|chunk|citation|done", "data": {...}}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request_data = json.loads(data)

            message = request_data.get("message", "")
            thread_id = request_data.get("thread_id", str(uuid.uuid4()))

            if not message:
                await websocket.send_json({"type": "error", "data": "Empty message"})
                continue

            try:
                from src.agents.supervisor import create_platform_graph, stream_agent

                graph = create_platform_graph()

                # Stream events
                async for event in stream_agent(
                    graph=graph,
                    user_message=message,
                    thread_id=thread_id,
                ):
                    node = event.get("node", "")
                    output = event.get("output", {})

                    if node == "supervisor":
                        await websocket.send_json({
                            "type": "routing",
                            "data": {
                                "agent": output.get("next_agent", ""),
                                "reasoning": output.get("metadata", {}).get(
                                    "last_reasoning", ""
                                ),
                            },
                        })
                    elif node in ("rag_agent", "sql_agent", "api_agent", "doc_agent"):
                        messages = output.get("messages", [])
                        for msg in messages:
                            if hasattr(msg, "content"):
                                await websocket.send_json({
                                    "type": "chunk",
                                    "data": {
                                        "agent": node,
                                        "content": msg.content,
                                    },
                                })

                        # Send citations if available
                        citations = output.get("citations", [])
                        if citations:
                            await websocket.send_json({
                                "type": "citations",
                                "data": citations,
                            })

                # Signal completion
                await websocket.send_json({
                    "type": "done",
                    "data": {"thread_id": thread_id},
                })

            except Exception as e:
                logger.error(f"WebSocket stream error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
