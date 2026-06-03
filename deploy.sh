#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  JARVIS — Deploy Script (Linux/macOS)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[ERROR] .env file not found!"
    echo "[INFO] Copy .env.production to .env and fill in your values."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker not found. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[ERROR] docker-compose not found."
    exit 1
fi

# Detect docker compose command
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

echo "[1/5] Stopping any existing containers..."
$COMPOSE down --remove-orphans 2> /dev/null || true

echo ""
echo "[2/5] Building containers..."
$COMPOSE build --no-cache

echo ""
echo "[3/5] Starting services..."
$COMPOSE up -d

echo ""
echo "[4/5] Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health/live > /dev/null 2>&1; then
        echo "[OK] Backend is healthy!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "[5/5] Checking frontend..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "[OK] Frontend is up!"
else
    echo "[WARN] Frontend not ready yet. It may need a few more seconds."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  JARVIS is running!"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/v1/docs"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Commands:"
echo "  $COMPOSE logs -f backend    # View backend logs"
echo "  $COMPOSE logs -f frontend   # View frontend logs"
echo "  $COMPOSE down                # Stop everything"
echo ""
