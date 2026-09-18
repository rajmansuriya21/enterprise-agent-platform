"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Enterprise Multi-Agent Platform"
        assert data["version"] == "1.0.0"

    def test_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_docs_available(self):
        response = client.get("/docs")
        assert response.status_code == 200


class TestMetricsEndpoint:
    """Tests for the metrics endpoint."""

    def test_get_metrics(self):
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "requests_total" in data
        assert "agent_invocations" in data

    def test_prometheus_metrics(self):
        response = client.get("/api/v1/metrics/prometheus")
        assert response.status_code == 200
        text = response.text
        assert "agent_platform_uptime_seconds" in text


class TestChatEndpoint:
    """Tests for the chat endpoint."""

    def test_chat_missing_message(self):
        response = client.post("/api/v1/chat", json={"message": ""})
        assert response.status_code == 422  # Validation error


class TestDocumentEndpoints:
    """Tests for document endpoints."""

    def test_list_documents(self):
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
