"""
Metrics Routes — Prometheus-compatible metrics export.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory metrics store (production would use prometheus_client)
_metrics: dict[str, Any] = {
    "requests_total": 0,
    "agent_invocations": {
        "supervisor": 0,
        "rag_agent": 0,
        "sql_agent": 0,
        "api_agent": 0,
        "doc_agent": 0,
    },
    "tool_calls_total": 0,
    "tool_calls_success": 0,
    "latency_samples": [],
    "start_time": time.time(),
}


class MetricsResponse(BaseModel):
    """Metrics summary."""

    uptime_seconds: float
    requests_total: int
    agent_invocations: dict[str, int]
    tool_call_success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    documents_indexed: int


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """Get platform metrics in JSON format."""
    uptime = time.time() - _metrics["start_time"]

    latencies = _metrics["latency_samples"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    sorted_latencies = sorted(latencies)
    p95_latency = (
        sorted_latencies[int(len(sorted_latencies) * 0.95)]
        if sorted_latencies
        else 0
    )

    tool_total = _metrics["tool_calls_total"]
    tool_success = _metrics["tool_calls_success"]
    success_rate = tool_success / tool_total if tool_total > 0 else 1.0

    # Get document count from vector store
    doc_count = 0
    try:
        from src.services.vector_store import get_vector_store

        vs = get_vector_store()
        info = vs.collection_info()
        doc_count = info.get("points_count", 0)
    except Exception:
        pass

    return MetricsResponse(
        uptime_seconds=round(uptime, 2),
        requests_total=_metrics["requests_total"],
        agent_invocations=_metrics["agent_invocations"],
        tool_call_success_rate=round(success_rate, 4),
        avg_latency_ms=round(avg_latency, 2),
        p95_latency_ms=round(p95_latency, 2),
        documents_indexed=doc_count,
    )


@router.get("/metrics/prometheus")
async def prometheus_metrics() -> str:
    """Export metrics in Prometheus text format."""
    uptime = time.time() - _metrics["start_time"]
    lines = [
        "# HELP agent_platform_uptime_seconds Platform uptime in seconds",
        "# TYPE agent_platform_uptime_seconds gauge",
        f"agent_platform_uptime_seconds {uptime:.2f}",
        "",
        "# HELP agent_platform_requests_total Total API requests",
        "# TYPE agent_platform_requests_total counter",
        f"agent_platform_requests_total {_metrics['requests_total']}",
        "",
        "# HELP agent_invocations_total Agent invocations by agent type",
        "# TYPE agent_invocations_total counter",
    ]

    for agent, count in _metrics["agent_invocations"].items():
        lines.append(f'agent_invocations_total{{agent="{agent}"}} {count}')

    lines.extend([
        "",
        "# HELP tool_calls_total Total tool calls",
        "# TYPE tool_calls_total counter",
        f"tool_calls_total {_metrics['tool_calls_total']}",
        "",
        "# HELP tool_calls_success_total Successful tool calls",
        "# TYPE tool_calls_success_total counter",
        f"tool_calls_success_total {_metrics['tool_calls_success']}",
    ])

    return "\n".join(lines) + "\n"


# ── Metric Recording Helpers ────────────────────────────────
def record_request() -> None:
    """Record an API request."""
    _metrics["requests_total"] += 1


def record_agent_invocation(agent_name: str) -> None:
    """Record an agent invocation."""
    if agent_name in _metrics["agent_invocations"]:
        _metrics["agent_invocations"][agent_name] += 1


def record_tool_call(success: bool) -> None:
    """Record a tool call result."""
    _metrics["tool_calls_total"] += 1
    if success:
        _metrics["tool_calls_success"] += 1


def record_latency(latency_ms: float) -> None:
    """Record a latency sample."""
    _metrics["latency_samples"].append(latency_ms)
    # Keep only last 1000 samples
    if len(_metrics["latency_samples"]) > 1000:
        _metrics["latency_samples"] = _metrics["latency_samples"][-1000:]
