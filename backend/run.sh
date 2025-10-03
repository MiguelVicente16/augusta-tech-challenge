#!/bin/bash

# Portuguese Public Incentives API - Startup Script
#
# Usage:
#   ./run.sh              # Start in development mode with auto-reload
#   ./run.sh prod         # Start in production mode
#   ./run.sh --help       # Show help

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║    Portuguese Public Incentives API                           ║"
echo "║    FastAPI Server Startup                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "   Create one from .env.example:"
    echo "   cp .env.example .env"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
HOST=${API_HOST:-"0.0.0.0"}
PORT=${API_PORT:-8000}
WORKERS=${API_WORKERS:-1}
ENVIRONMENT=${ENVIRONMENT:-"development"}

# Parse arguments
MODE="dev"
if [ "$1" == "prod" ] || [ "$1" == "production" ]; then
    MODE="prod"
    ENVIRONMENT="production"
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage:"
    echo "  ./run.sh              Start in development mode (auto-reload)"
    echo "  ./run.sh prod         Start in production mode"
    echo "  ./run.sh --help       Show this help"
    echo ""
    echo "Environment variables (set in .env):"
    echo "  API_HOST              Host to bind (default: 0.0.0.0)"
    echo "  API_PORT              Port to listen (default: 8000)"
    echo "  API_WORKERS           Number of workers (default: 1)"
    echo "  DB_HOST               Database host"
    echo "  DB_PORT               Database port"
    echo "  DB_NAME               Database name"
    echo ""
    exit 0
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi

# Check if virtual environment should be used
if [ -d "venv" ]; then
    echo -e "${BLUE}→ Activating virtual environment (venv)${NC}"
    source venv/bin/activate
elif [ ! -z "$CONDA_DEFAULT_ENV" ]; then
    echo -e "${BLUE}→ Using conda environment: ${CONDA_DEFAULT_ENV}${NC}"
else
    echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
    echo -e "   Using system Python. Consider creating a venv or activating conda env first."
fi

# Check dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  FastAPI not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

echo ""
echo -e "${GREEN}✓ Starting API Server${NC}"
echo -e "  Mode:        ${YELLOW}${MODE}${NC}"
echo -e "  Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "  URL:         ${BLUE}http://${HOST}:${PORT}${NC}"
echo -e "  Docs:        ${BLUE}http://${HOST}:${PORT}/docs${NC}"
echo -e "  Health:      ${BLUE}http://${HOST}:${PORT}/health${NC}"
echo ""

# Start server
if [ "$MODE" == "dev" ]; then
    echo -e "${BLUE}→ Starting in development mode (auto-reload enabled)${NC}"
    echo ""
    uvicorn src.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level info
else
    echo -e "${BLUE}→ Starting in production mode${NC}"
    echo -e "  Workers: ${WORKERS}"
    echo ""
    uvicorn src.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level warning
fi
