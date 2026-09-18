"""
MLflow Configuration — Experiment tracking and model management.

Sets up MLflow tracing for LangChain/LangGraph with autologging,
custom metric logging, and model registry integration.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


def setup_mlflow() -> bool:
    """Initialize MLflow experiment tracking.

    Returns:
        True if MLflow was set up successfully, False otherwise.
    """
    settings = get_settings()

    try:
        import mlflow

        # Configure tracking
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)

        # Enable LangChain autologging
        mlflow.langchain.autolog(
            log_models=True,
            log_input_examples=True,
        )

        logger.info(
            f"✅ MLflow configured: uri={settings.mlflow_tracking_uri}, "
            f"experiment={settings.mlflow_experiment_name}"
        )
        return True

    except ImportError:
        logger.warning("⚠️ MLflow not installed. Tracing disabled.")
        return False
    except Exception as e:
        logger.warning(f"⚠️ MLflow setup failed: {e}. Tracing disabled.")
        return False


def log_agent_metrics(
    agent_name: str,
    latency_ms: float,
    tokens_used: int = 0,
    success: bool = True,
    tools_called: list[str] | None = None,
) -> None:
    """Log agent invocation metrics to MLflow.

    Args:
        agent_name: Name of the agent.
        latency_ms: Response latency in milliseconds.
        tokens_used: Number of tokens consumed.
        success: Whether the invocation was successful.
        tools_called: List of tools invoked.
    """
    try:
        import mlflow

        with mlflow.start_run(nested=True, run_name=f"agent_{agent_name}"):
            mlflow.log_metrics({
                f"{agent_name}_latency_ms": latency_ms,
                f"{agent_name}_tokens": tokens_used,
                f"{agent_name}_success": 1 if success else 0,
            })

            mlflow.log_params({
                "agent": agent_name,
                "tools": ",".join(tools_called or []),
            })

    except Exception as e:
        logger.debug(f"MLflow logging skipped: {e}")


def log_rag_evaluation(
    recall_at_k: float,
    precision_at_k: float,
    hallucination_rate: float,
    citation_accuracy: float,
) -> None:
    """Log RAG evaluation metrics to MLflow."""
    try:
        import mlflow

        mlflow.log_metrics({
            "rag_recall_at_5": recall_at_k,
            "rag_precision_at_5": precision_at_k,
            "rag_hallucination_rate": hallucination_rate,
            "rag_citation_accuracy": citation_accuracy,
        })

    except Exception as e:
        logger.debug(f"MLflow RAG logging skipped: {e}")
