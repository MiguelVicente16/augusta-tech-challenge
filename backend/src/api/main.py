"""
FastAPI application for Portuguese Public Incentives System

Main application entry point with API configuration and routers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..database.connection import DatabaseManager
from ..database.service import DatabaseService
from ..config import Settings
from . import dependencies

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors (no debug/info spam)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database manager instance
db_manager: DatabaseManager = None
db_service: DatabaseService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application
    Handles startup and shutdown events
    """
    # Startup
    global db_manager, db_service
    settings = Settings()

    logger.info("Starting up FastAPI application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database
    try:
        db_manager = DatabaseManager()
        await db_manager.connect()
        db_service = DatabaseService(db_manager)

        # Set global db_service for dependencies
        dependencies.set_db_service(db_service)

        # Create schema if it doesn't exist
        await db_service.create_schema()

        logger.info("Database connected and schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    if db_manager:
        await db_manager.close()
        logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Portuguese Public Incentives API",
    description="Sistema inteligente para identificação e matching de incentivos públicos",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (import here to avoid circular imports)
from .routers import csv_loader, embeddings, inspection, matching, chatbot, data

app.include_router(csv_loader.router, prefix="/api/v1", tags=["Data Loading"])
app.include_router(embeddings.router, prefix="/api/v1", tags=["embeddings"])
app.include_router(inspection.router, prefix="/api/v1/inspect", tags=["Database Inspection"])
app.include_router(matching.router, prefix="/api/v1", tags=["Matching"])
app.include_router(chatbot.router, prefix="/api/v1", tags=["Chatbot"])
app.include_router(data.router, prefix="/api/v1", tags=["Data Access"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Portuguese Public Incentives API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint

    For detailed database health, use GET /api/v1/inspect/health
    """
    try:
        # Quick check - just verify database is accessible
        count = await db_service.count_incentives()
        return {
            "status": "healthy",
            "database": "connected",
            "message": "API is running. Use /api/v1/inspect/health for detailed database info."
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }


# Export for external access
__all__ = ["app"]
