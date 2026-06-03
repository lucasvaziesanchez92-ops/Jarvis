.PHONY: help install run test lint format clean seed docker-build docker-run db-init db-migrate

# ── Help ──────────────────────────────────────────────────────
help:
	@echo "Jarvis AI Assistant - Makefile Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install        Install all dependencies (backend + mobile)"
	@echo ""
	@echo "Development:"
	@echo "  run            Start backend server with auto-reload"
	@echo "  run-mobile     Start Expo dev server"
	@echo "  run-all        Start backend + mobile"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests"
	@echo "  test-cov       Run tests with coverage report"
	@echo "  test-phase2    Run phase 2 tests (no Bedrock needed)"
	@echo "  test-phase3    Run phase 3 tests (API endpoints)"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           Run ruff linter on backend"
	@echo "  lint-mobile    Run TypeScript check on mobile"
	@echo "  format         Auto-format code with ruff"
	@echo "  type-check     Run mypy type checker"
	@echo ""
	@echo "Database:"
	@echo "  db-init        Initialize database with seed data"
	@echo "  db-migrate     Run Alembic migrations"
	@echo "  db-revision    Create new migration (usage: make db-revision MESSAGE='add column')"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-run     Run with Docker Compose"
	@echo "  docker-stop    Stop Docker Compose services"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          Remove cache, build artifacts, and logs"

# ── Setup ─────────────────────────────────────────────────────
install:
	@echo "Installing backend dependencies..."
	pip install -r requirements.txt
	@echo "Installing mobile dependencies..."
	cd mobile && npm install
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Installation complete!"

# ── Development ──────────────────────────────────────────────
run:
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

run-mobile:
	cd mobile && npx expo start

run-all:
	@echo "Starting backend and mobile..."
	start cmd /k "uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000"
	cd mobile && npx expo start

# ── Testing ──────────────────────────────────────────────────
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=backend --cov-report=term-missing --cov-report=html

test-phase2:
	pytest tests/phase2/ -v

test-phase3:
	pytest tests/phase3/ -v

# ── Code Quality ─────────────────────────────────────────────
lint:
	ruff check backend/ tests/
	ruff format --check backend/ tests/

lint-mobile:
	cd mobile && npx tsc --noEmit

format:
	ruff check backend/ tests/ --fix
	ruff format backend/ tests/

type-check:
	mypy backend/ --ignore-missing-imports

# ── Database ─────────────────────────────────────────────────
db-init:
	@echo "Seeding database with sample data..."
	python backend/scripts/seed_data.py

db-migrate:
	@echo "Running Alembic migrations..."
	alembic upgrade head

db-revision:
	@echo "Creating new migration..."
	alembic revision --autogenerate -m "$(MESSAGE)"

# ── Docker ───────────────────────────────────────────────────
docker-build:
	docker build -t jarvis:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# ── Cleanup ──────────────────────────────────────────────────
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf data/logs/*.log
	rm -rf data/audit_logs/*.jsonl
	rm -rf data/token_logs/*.jsonl
	@echo "Cleanup complete!"
