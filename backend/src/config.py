import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/incentivos"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "incentivos"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"

    # Database Pool Configuration
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    DB_POOL_TIMEOUT: float = 30.0

    # AI Configuration
    AI_PROVIDER: str = "openai"  # "openai" or "gemini"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ENABLE_AI_GENERATION: bool = False
    OPENAI_MODEL: str = "gpt-5-mini"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    MAX_COST_PER_INCENTIVE: float = 0.30
    
    # Rate Limiting Configuration
    AI_REQUESTS_PER_MINUTE: int = 10  # Max requests per minute to avoid rate limits
    AI_REQUEST_DELAY_SECONDS: float = 6.0  # Minimum delay between requests (60/10 = 6 seconds)

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8004
    API_WORKERS: int = 1
    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def async_database_url(self) -> str:
        """Get async database URL for asyncpg"""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()