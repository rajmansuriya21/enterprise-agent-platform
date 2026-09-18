"""Tests for the evaluation metrics module."""

from src.utils.evaluation import (
    EvaluationSuite,
    LatencyTracker,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


class TestRetrievalMetrics:
    """Tests for retrieval evaluation metrics."""

    def test_perfect_recall(self):
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1", "doc2", "doc3"]
        assert recall_at_k(retrieved, relevant, k=5) == 1.0

    def test_partial_recall(self):
        retrieved = ["doc1", "doc2", "doc4"]
        relevant = ["doc1", "doc2", "doc3"]
        assert recall_at_k(retrieved, relevant, k=5) == pytest.approx(2 / 3)

    def test_zero_recall(self):
        retrieved = ["doc4", "doc5"]
        relevant = ["doc1", "doc2"]
        assert recall_at_k(retrieved, relevant, k=5) == 0.0

    def test_empty_relevant(self):
        assert recall_at_k(["doc1"], [], k=5) == 0.0

    def test_precision(self):
        retrieved = ["doc1", "doc2", "doc4", "doc5"]
        relevant = ["doc1", "doc2", "doc3"]
        assert precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_mrr_first_position(self):
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = ["doc1"]
        assert mean_reciprocal_rank(retrieved, relevant) == 1.0

    def test_mrr_second_position(self):
        retrieved = ["doc2", "doc1", "doc3"]
        relevant = ["doc1"]
        assert mean_reciprocal_rank(retrieved, relevant) == 0.5

    def test_mrr_not_found(self):
        retrieved = ["doc2", "doc3"]
        relevant = ["doc1"]
        assert mean_reciprocal_rank(retrieved, relevant) == 0.0


class TestLatencyTracker:
    """Tests for the latency tracker."""

    def test_record_and_stats(self):
        tracker = LatencyTracker()
        for val in [100, 200, 300, 400, 500]:
            tracker.record(val)

        assert tracker.count == 5
        assert tracker.mean == 300.0
        assert tracker.p50 == 300.0

    def test_empty_tracker(self):
        tracker = LatencyTracker()
        assert tracker.count == 0
        assert tracker.mean == 0.0
        assert tracker.p50 == 0.0

    def test_summary(self):
        tracker = LatencyTracker()
        tracker.record(100)
        tracker.record(200)
        summary = tracker.summary()
        assert "count" in summary
        assert "mean_ms" in summary
        assert "p50_ms" in summary
        assert "p95_ms" in summary


class TestEvaluationSuite:
    """Tests for the comprehensive evaluation suite."""

    def test_tool_call_tracking(self):
        suite = EvaluationSuite()
        suite.record_tool_call(True)
        suite.record_tool_call(True)
        suite.record_tool_call(False)

        assert suite.tool_call_success_rate == pytest.approx(2 / 3)

    def test_retrieval_recording(self):
        suite = EvaluationSuite()
        scores = suite.record_retrieval(
            retrieved=["d1", "d2", "d3"],
            relevant=["d1", "d2"],
            k=5,
        )
        assert scores["recall_at_k"] == 1.0
        assert scores["precision_at_k"] == pytest.approx(2 / 3)

    def test_summary(self):
        suite = EvaluationSuite()
        suite.record_tool_call(True)
        suite.latency_tracker.record(100)
        summary = suite.summary()
        assert "latency" in summary
        assert "tool_call_success_rate" in summary


# Required for approx assertions
import pytest
