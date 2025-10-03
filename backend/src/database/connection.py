import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool

from ..config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections using asyncpg"""

    def __init__(self):
        self.pool: Optional[Pool] = None
        self.settings = get_settings()

    async def connect(self) -> None:
        """Initialize database connection pool"""
        try:
            logger.info("Initializing database connection pool...")

            self.pool = await asyncpg.create_pool(
                host=self.settings.DB_HOST,
                port=self.settings.DB_PORT,
                database=self.settings.DB_NAME,
                user=self.settings.DB_USER,
                password=self.settings.DB_PASSWORD,
                min_size=self.settings.DB_POOL_MIN_SIZE,
                max_size=self.settings.DB_POOL_MAX_SIZE,
                command_timeout=self.settings.DB_POOL_TIMEOUT,
            )

            # Test connection
            async with self.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")

            logger.info("Database connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self.pool:
            logger.info("Closing database connection pool...")
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def close(self) -> None:
        """Alias for disconnect() for backwards compatibility"""
        await self.disconnect()

    async def initialize(self) -> None:
        """Alias for connect() for backwards compatibility"""
        await self.connect()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get database connection with transaction"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as connection:
            async with connection.transaction():
                try:
                    yield connection
                except Exception as e:
                    logger.error(f"Database transaction failed: {e}")
                    raise

    async def execute_script(self, script: str) -> None:
        """Execute SQL script"""
        async with self.get_connection() as connection:
            await connection.execute(script)

    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_connection() as connection:
                result = await connection.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> DatabaseManager:
    """FastAPI dependency for database manager"""
    return db_manager


async def startup_database():
    """Startup event for FastAPI"""
    await db_manager.connect()


async def shutdown_database():
    """Shutdown event for FastAPI"""
    await db_manager.disconnect()