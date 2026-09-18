"""
RAG Evaluation Metrics — Automated quality assessment for retrieval and generation.

Implements RAGAS-style evaluation metrics including:
- Retrieval Recall@K and Precision@K
- Hallucination detection
- Citation accuracy scoring
- Response relevance scoring
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.utils.prompts import HALLUCINATION_CHECK_PROMPT, CITATION_ACCURACY_PROMPT

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Retrieval Metrics
# ──────────────────────────────────────────────────────────────
def recall_at_k(
    retrieved_docs: list[str],
    relevant_docs: list[str],
    k: int = 5,
) -> float:
    """Calculate Recall@K for retrieval evaluation.

    Args:
        retrieved_docs: List of retrieved document IDs (top K).
        relevant_docs: List of ground-truth relevant document IDs.
        k: Number of top results to consider.

    Returns:
        Recall@K score (0.0 to 1.0).
    """
    if not relevant_docs:
        return 0.0

    top_k = set(retrieved_docs[:k])
    relevant = set(relevant_docs)
    hits = top_k & relevant

    return len(hits) / len(relevant)


def precision_at_k(
    retrieved_docs: list[str],
    relevant_docs: list[str],
    k: int = 5,
) -> float:
    """Calculate Precision@K for retrieval evaluation.

    Args:
        retrieved_docs: List of retrieved document IDs (top K).
        relevant_docs: List of ground-truth relevant document IDs.
        k: Number of top results to consider.

    Returns:
        Precision@K score (0.0 to 1.0).
    """
    top_k = retrieved_docs[:k]
    if not top_k:
        return 0.0

    relevant = set(relevant_docs)
    hits = sum(1 for doc in top_k if doc in relevant)

    return hits / len(top_k)


def mean_reciprocal_rank(
    retrieved_docs: list[str],
    relevant_docs: list[str],
) -> float:
    """Calculate Mean Reciprocal Rank (MRR).

    Args:
        retrieved_docs: List of retrieved document IDs.
        relevant_docs: List of ground-truth relevant document IDs.

    Returns:
        MRR score (0.0 to 1.0).
    """
    relevant = set(relevant_docs)
    for i, doc in enumerate(retrieved_docs):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


# ──────────────────────────────────────────────────────────────
# Generation Quality Metrics
# ──────────────────────────────────────────────────────────────
async def check_hallucination(
    llm: Any,
    context: str,
    response: str,
) -> dict[str, Any]:
    """Check a response for hallucinated content not grounded in context.

    Uses an LLM as a judge to evaluate whether each claim in the response
    is supported by the provided context.

    Args:
        llm: LLM instance for evaluation.
        context: The retrieved context used for generation.
        response: The generated response to evaluate.

    Returns:
        Dictionary with verdict, confidence, unsupported claims, and reasoning.
    """
    try:
        prompt = HALLUCINATION_CHECK_PROMPT.format(
            context=context, response=response
        )
        result = await llm.ainvoke(prompt)

        # Try to parse as JSON
        try:
            parsed = json.loads(result.content)
            return parsed
        except json.JSONDecodeError:
            return {
                "verdict": "UNKNOWN",
                "confidence": 0.0,
                "unsupported_claims": [],
                "reasoning": result.content,
            }
    except Exception as e:
        logger.error(f"Hallucination check failed: {e}")
        return {
            "verdict": "ERROR",
            "confidence": 0.0,
            "unsupported_claims": [],
            "reasoning": str(e),
        }


async def check_citation_accuracy(
    llm: Any,
    sources: str,
    response: str,
) -> dict[str, Any]:
    """Verify that citations in a response correctly reference source material.

    Args:
        llm: LLM instance for evaluation.
        sources: The source documents.
        response: The response with citations to verify.

    Returns:
        Dictionary with citation accuracy metrics.
    """
    try:
        prompt = CITATION_ACCURACY_PROMPT.format(
            sources=sources, response=response
        )
        result = await llm.ainvoke(prompt)

        try:
            parsed = json.loads(result.content)
            return parsed
        except json.JSONDecodeError:
            return {
                "total_citations": 0,
                "accurate_citations": 0,
                "accuracy_score": 0.0,
                "issues": [result.content],
            }
    except Exception as e:
        logger.error(f"Citation accuracy check failed: {e}")
        return {
            "total_citations": 0,
            "accurate_citations": 0,
            "accuracy_score": 0.0,
            "issues": [str(e)],
        }


# ──────────────────────────────────────────────────────────────
# Latency Tracking
# ──────────────────────────────────────────────────────────────
class LatencyTracker:
    """Track and compute latency percentiles for agent operations."""

    def __init__(self) -> None:
        self._latencies: list[float] = []

    def record(self, latency_ms: float) -> None:
        """Record a latency measurement in milliseconds."""
        self._latencies.append(latency_ms)

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile of recorded latencies."""
        if not self._latencies:
            return 0.0
        sorted_latencies = sorted(self._latencies)
        idx = int(len(sorted_latencies) * p / 100)
        idx = min(idx, len(sorted_latencies) - 1)
        return sorted_latencies[idx]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def mean(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    @property
    def count(self) -> int:
        return len(self._latencies)

    def summary(self) -> dict[str, float]:
        return {
            "count": self.count,
            "mean_ms": round(self.mean, 2),
            "p50_ms": round(self.p50, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
        }


# ──────────────────────────────────────────────────────────────
# Comprehensive Evaluation Suite
# ──────────────────────────────────────────────────────────────
class EvaluationSuite:
    """Complete evaluation suite for RAG pipeline assessment."""

    def __init__(self) -> None:
        self.latency_tracker = LatencyTracker()
        self.tool_call_results: list[bool] = []
        self.hallucination_results: list[dict] = []
        self.retrieval_scores: list[dict] = []

    def record_tool_call(self, success: bool) -> None:
        """Record a tool call result."""
        self.tool_call_results.append(success)

    @property
    def tool_call_success_rate(self) -> float:
        if not self.tool_call_results:
            return 0.0
        return sum(self.tool_call_results) / len(self.tool_call_results)

    def record_retrieval(
        self, retrieved: list[str], relevant: list[str], k: int = 5
    ) -> dict[str, float]:
        """Record and compute retrieval metrics."""
        scores = {
            "recall_at_k": recall_at_k(retrieved, relevant, k),
            "precision_at_k": precision_at_k(retrieved, relevant, k),
            "mrr": mean_reciprocal_rank(retrieved, relevant),
        }
        self.retrieval_scores.append(scores)
        return scores

    def summary(self) -> dict[str, Any]:
        """Generate a comprehensive evaluation summary."""
        avg_retrieval = {}
        if self.retrieval_scores:
            keys = self.retrieval_scores[0].keys()
            avg_retrieval = {
                k: round(
                    sum(s[k] for s in self.retrieval_scores) / len(self.retrieval_scores),
                    4,
                )
                for k in keys
            }

        return {
            "latency": self.latency_tracker.summary(),
            "tool_call_success_rate": round(self.tool_call_success_rate, 4),
            "total_tool_calls": len(self.tool_call_results),
            "retrieval_metrics": avg_retrieval,
            "hallucination_checks": len(self.hallucination_results),
        }
