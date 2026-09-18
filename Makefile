.PHONY: help dev api streamlit test lint format docker-up docker-down seed benchmark clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────────────────
dev: ## Start both API and Streamlit for development
	@echo "Starting API server..."
	@uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "Starting Streamlit..."
	@streamlit run streamlit_app/app.py --server.port 8501

api: ## Start FastAPI server only
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

streamlit: ## Start Streamlit frontend only
	streamlit run streamlit_app/app.py --server.port 8501

# ── Testing ──────────────────────────────────────────────────
test: ## Run test suite
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# ── Code Quality ─────────────────────────────────────────────
lint: ## Run linter (ruff)
	ruff check src/ tests/ scripts/
	ruff format --check src/ tests/ scripts/

format: ## Format code (ruff)
	ruff check --fix src/ tests/ scripts/
	ruff format src/ tests/ scripts/

typecheck: ## Run type checker (mypy)
	mypy src/

# ── Docker ───────────────────────────────────────────────────
docker-up: ## Start all services via Docker Compose
	docker compose up -d --build

docker-down: ## Stop all Docker Compose services
	docker compose down -v

docker-logs: ## Tail Docker Compose logs
	docker compose logs -f

# ── Data ─────────────────────────────────────────────────────
seed: ## Seed sample data into Qdrant and SQLite
	python -m scripts.seed_data

benchmark: ## Run benchmark suite
	python -m scripts.benchmark

# ── Setup ────────────────────────────────────────────────────
install: ## Install project dependencies
	pip install -e ".[dev]"

setup-env: ## Create .env from template
	cp -n .env.example .env || true
	@echo "✅ Created .env — please fill in your API keys"

init: install setup-env seed ## Full project initialization
	@echo "✅ Project initialized successfully!"

# ── Cleanup ──────────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
