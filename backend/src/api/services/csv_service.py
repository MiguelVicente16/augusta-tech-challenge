"""
CSV Loading Service

Business logic layer for CSV loading operations.
Wraps database CSV loader with API-specific logic.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ...database.service import DatabaseService
from ...database.csv_loader import CSVLoader
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CSVLoadingService:
    """Service for CSV loading operations"""

    def __init__(self, db_service: DatabaseService):
        """
        Initialize CSV loading service

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service

    async def load_incentives(
        self,
        file_path: Path,
        enable_ai_generation: bool = False,
        batch_size: int = 1000,
        ai_provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load incentives from CSV file

        Args:
            file_path: Path to incentives CSV file
            enable_ai_generation: Enable AI-powered structured description generation
            batch_size: Batch size for processing
            ai_provider: AI provider to use ("openai" or "gemini", defaults to config setting)
            api_key: Optional API key (reads from env if not provided)

        Returns:
            Dict with loading results and statistics
        """
        logger.info(f"Loading incentives from {file_path}")

        # Use config default if no provider specified
        effective_ai_provider = ai_provider or settings.AI_PROVIDER

        # Initialize CSV loader
        loader = CSVLoader(
            db_service=self.db_service,
            ai_provider=effective_ai_provider,
            api_key=api_key,
            enable_ai_generation=enable_ai_generation
        )

        # Load CSV
        result = await loader.load_incentives_csv(
            file_path=file_path,
            batch_size=batch_size
        )

        return result

    async def load_companies(
        self,
        file_path: Path,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Load companies from CSV file

        Args:
            file_path: Path to companies CSV file
            batch_size: Batch size for processing

        Returns:
            Dict with loading results and statistics
        """
        logger.info(f"Loading companies from {file_path}")

        # Initialize CSV loader (no AI needed for companies)
        loader = CSVLoader(
            db_service=self.db_service,
            enable_ai_generation=False
        )

        # Load CSV
        result = await loader.load_companies_csv(
            file_path=file_path,
            batch_size=batch_size
        )

        return result

    async def load_all(
        self,
        data_dir: Path = Path("data"),
        enable_ai_generation: bool = False,
        batch_size: int = 1000,
        ai_provider: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load all CSV files (incentives + companies)

        Args:
            data_dir: Directory containing CSV files
            enable_ai_generation: Enable AI-powered structured description generation
            batch_size: Batch size for processing
            ai_provider: AI provider to use ("openai" or "gemini", defaults to config setting)
            api_key: Optional API key (reads from env if not provided)

        Returns:
            Dict with loading results for both files
        """
        logger.info(f"Loading all CSVs from {data_dir}")

        # Use config default if no provider specified
        effective_ai_provider = ai_provider or settings.AI_PROVIDER

        # Initialize CSV loader
        loader = CSVLoader(
            db_service=self.db_service,
            ai_provider=effective_ai_provider,
            api_key=api_key,
            enable_ai_generation=enable_ai_generation
        )

        # Load all CSVs
        result = await loader.load_all_csvs(data_dir=data_dir)

        return result
