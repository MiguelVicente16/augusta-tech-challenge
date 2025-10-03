import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd

from .models import IncentiveModel, CompanyModel
from .service import DatabaseService
from ..ai.client_factory import AIClientFactory
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CSVValidationError(Exception):
    """Custom exception for CSV validation errors"""
    pass


class CSVLoader:
    """Handles loading and validation of CSV data with robust error handling"""

    def __init__(
        self,
        db_service: DatabaseService,
        ai_provider: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_ai_generation: bool = False
    ):
        """
        Initialize CSV loader

        Args:
            db_service: Database service instance
            ai_provider: AI provider to use ("openai" or "gemini", defaults to config setting)
            api_key: API key (optional, reads from env if not provided)
            enable_ai_generation: Whether to generate structured descriptions with AI
        """
        self.db_service = db_service
        self.validation_errors: List[str] = []
        self.enable_ai_generation = enable_ai_generation
        self.ai_provider = ai_provider or settings.AI_PROVIDER

        # Initialize AI client if enabled
        if self.enable_ai_generation:
            try:
                self.description_generator = AIClientFactory.create_generator(
                    provider=self.ai_provider,
                    api_key=api_key
                )
                self.ai_client = self.description_generator.client
                logger.info(f"AI-powered structured description generation enabled ({ai_provider})")
            except (ValueError, RuntimeError) as e:
                logger.warning(f"Failed to initialize {ai_provider} client: {e}")
                logger.warning("Proceeding without AI generation")
                self.enable_ai_generation = False
        else:
            self.ai_client = None
            self.description_generator = None

    def validate_file_exists(self, file_path: Path) -> None:
        """Validate that CSV file exists and is readable"""
        if not file_path.exists():
            raise CSVValidationError(f"CSV file not found: {file_path}")

        if not file_path.is_file():
            raise CSVValidationError(f"Path is not a file: {file_path}")

        if file_path.suffix.lower() != '.csv':
            raise CSVValidationError(f"File is not a CSV: {file_path}")

    def clean_string_field(self, value: Any) -> Optional[str]:
        """Clean and validate string fields"""
        if pd.isna(value) or value is None:
            return None

        if isinstance(value, (int, float)):
            return str(value) if not pd.isna(value) else None

        # Clean string
        cleaned = str(value).strip()
        return cleaned if cleaned else None

    def parse_json_field(self, value: Any, field_name: str, row_index: int) -> Optional[Dict[str, Any]]:
        """Parse JSON field with error handling"""
        if pd.isna(value) or value is None:
            return None

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in {field_name} at row {row_index}: {e}"
                logger.warning(error_msg)
                self.validation_errors.append(error_msg)
                return {}

        # Handle other types (like lists, etc.) by converting to JSON-serializable
        try:
            if hasattr(value, '__dict__'):
                return value.__dict__
            else:
                # Try to convert to string and back to JSON
                json_str = json.dumps(value, default=str)
                return json.loads(json_str)
        except (TypeError, json.JSONDecodeError) as e:
            error_msg = f"Cannot convert {field_name} to JSON at row {row_index}: {e}"
            logger.warning(error_msg)
            self.validation_errors.append(error_msg)
            return {}

    def parse_decimal_field(self, value: Any, field_name: str, row_index: int) -> Optional[Decimal]:
        """Parse decimal field with error handling"""
        if pd.isna(value) or value is None:
            return None

        try:
            if isinstance(value, str):
                # Remove common formatting characters
                cleaned = value.replace(',', '').replace('€', '').replace('$', '').strip()
                if not cleaned:
                    return None
                return Decimal(cleaned)
            elif isinstance(value, (int, float)):
                return Decimal(str(value))
            else:
                return Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            error_msg = f"Invalid decimal in {field_name} at row {row_index}: {value} ({e})"
            logger.warning(error_msg)
            self.validation_errors.append(error_msg)
            return None

    def parse_date_field(self, value: Any, field_name: str, row_index: int) -> Optional[datetime]:
        """Parse date field with multiple format support"""
        if pd.isna(value) or value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            # Try common date formats including datetime with timezone
            date_formats = [
                '%Y-%m-%d %H:%M:%S+%f',  # 2024-03-05 09:35:00+00
                '%Y-%m-%d %H:%M:%S%z',   # 2024-03-05 09:35:00+0000
                '%Y-%m-%d %H:%M:%S',     # 2024-03-05 09:35:00
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
                '%d.%m.%Y',
                '%Y.%m.%d'
            ]

            for fmt in date_formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            # Try parsing ISO format with timezone
            try:
                from datetime import datetime as dt
                # Handle timezone format like +00
                if '+' in value and not value.endswith('+00'):
                    value = value.replace('+00', '')
                elif '+' in value and value.endswith('+00'):
                    value = value[:-3]  # Remove +00

                # Try parsing as ISO format
                parsed = dt.fromisoformat(value.replace('+00', ''))
                return parsed.date()
            except (ValueError, AttributeError):
                pass

            error_msg = f"Invalid date format in {field_name} at row {row_index}: {value}"
            logger.warning(error_msg)
            self.validation_errors.append(error_msg)
            return None

        return None

    def validate_incentive_row(self, row: pd.Series, index: int) -> Optional[IncentiveModel]:
        """Validate and convert a single incentive row to IncentiveModel"""
        try:
            # Required field validation
            title = self.clean_string_field(row.get('title'))
            if not title:
                error_msg = f"Missing required title at row {index}"
                logger.warning(error_msg)
                self.validation_errors.append(error_msg)
                return None

            # Parse optional fields with validation
            eligibility_criteria = self.parse_json_field(
                row.get('eligibility_criteria'), 'eligibility_criteria', index
            )

            document_urls = self.parse_json_field(
                row.get('document_urls'), 'document_urls', index
            )

            total_budget = self.parse_decimal_field(
                row.get('total_budget'), 'total_budget', index
            )

            date_publication = self.parse_date_field(
                row.get('date_publication'), 'date_publication', index
            )

            date_start = self.parse_date_field(
                row.get('date_start'), 'date_start', index
            )

            date_end = self.parse_date_field(
                row.get('date_end'), 'date_end', index
            )

            # Generate structured description with AI if enabled
            ai_description_structured = None
            if self.enable_ai_generation and self.description_generator:
                try:
                    ai_description_structured = self.description_generator.generate(
                        title=title,
                        description=self.clean_string_field(row.get('description')),
                        ai_description=self.clean_string_field(row.get('ai_description'))
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate structured description for row {index}: {e}")

            return IncentiveModel(
                incentive_project_id=self.clean_string_field(row.get('incentive_project_id')),
                project_id=self.clean_string_field(row.get('project_id')),
                title=title,
                description=self.clean_string_field(row.get('description')),
                ai_description=self.clean_string_field(row.get('ai_description')),
                ai_description_structured=ai_description_structured,
                eligibility_criteria=eligibility_criteria,
                document_urls=document_urls,
                date_publication=date_publication,
                date_start=date_start,
                date_end=date_end,
                total_budget=total_budget,
                source_link=self.clean_string_field(row.get('source_link')),
                status=self.clean_string_field(row.get('status'))
            )

        except Exception as e:
            error_msg = f"Error processing incentive row {index}: {e}"
            logger.error(error_msg)
            self.validation_errors.append(error_msg)
            return None

    def validate_company_row(self, row: pd.Series, index: int) -> Optional[CompanyModel]:
        """Validate and convert a single company row to CompanyModel"""
        try:
            # Required field validation
            company_name = self.clean_string_field(row.get('company_name'))
            if not company_name:
                error_msg = f"Missing required company_name at row {index}"
                logger.warning(error_msg)
                self.validation_errors.append(error_msg)
                return None

            return CompanyModel(
                company_name=company_name,
                cae_primary_label=self.clean_string_field(row.get('cae_primary_label')),
                trade_description_native=self.clean_string_field(row.get('trade_description_native')),
                website=self.clean_string_field(row.get('website'))
            )

        except Exception as e:
            error_msg = f"Error processing company row {index}: {e}"
            logger.error(error_msg)
            self.validation_errors.append(error_msg)
            return None

    async def load_incentives_csv(self, file_path: Path, batch_size: int = 1000) -> Dict[str, Any]:
        """Load incentives from CSV with validation and batch processing"""
        logger.info(f"Loading incentives from {file_path}")

        # Reset validation errors
        self.validation_errors = []

        # Validate file
        self.validate_file_exists(file_path)

        try:
            # Read CSV with proper encoding handling and error recovery
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except pd.errors.ParserError as e:
                logger.warning(f"CSV parsing error, trying with error_bad_lines=False: {e}")
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            except UnicodeDecodeError:
                logger.warning("UTF-8 encoding failed, trying latin-1")
                df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip')

            logger.info(f"Read {len(df)} rows from incentives CSV")

            if df.empty:
                raise CSVValidationError("CSV file is empty")

            # Check required columns
            required_columns = ['title']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise CSVValidationError(f"Missing required columns: {missing_columns}")

            # Process rows in batches
            valid_incentives = []
            total_processed = 0
            total_errors = 0

            for start_idx in range(0, len(df), batch_size):
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]

                batch_incentives = []
                for idx, row in batch_df.iterrows():
                    incentive = self.validate_incentive_row(row, idx)
                    if incentive:
                        batch_incentives.append(incentive)
                    else:
                        total_errors += 1

                # Insert batch if we have valid data
                if batch_incentives:
                    inserted_count = await self.db_service.batch_create_incentives(batch_incentives)
                    valid_incentives.extend(batch_incentives)
                    logger.info(f"Inserted batch {start_idx//batch_size + 1}: {inserted_count} incentives")

                total_processed += len(batch_df)

            result = {
                "total_rows": len(df),
                "processed_rows": total_processed,
                "valid_rows": len(valid_incentives),
                "error_rows": total_errors,
                "validation_errors": self.validation_errors[:50],  # Limit error list
                "success": True
            }

            # Add AI usage stats if enabled
            if self.enable_ai_generation and self.ai_client:
                result["ai_usage"] = self.ai_client.get_usage_summary()
                logger.info(f"AI Usage: {result['ai_usage']}")

            logger.info(f"Incentives loading completed: {result}")
            return result

        except Exception as e:
            error_msg = f"Failed to load incentives CSV: {e}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "validation_errors": self.validation_errors,
                "success": False
            }

    async def load_companies_csv(self, file_path: Path, batch_size: int = 1000) -> Dict[str, Any]:
        """Load companies from CSV with validation and batch processing"""
        logger.info(f"Loading companies from {file_path}")

        # Reset validation errors
        self.validation_errors = []

        # Validate file
        self.validate_file_exists(file_path)

        try:
            # Read CSV with proper encoding handling and error recovery
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except pd.errors.ParserError as e:
                logger.warning(f"CSV parsing error, trying with on_bad_lines='skip': {e}")
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                except pd.errors.ParserError:
                    logger.warning("Still failing, trying with quoting=csv.QUOTE_NONE")
                    import csv
                    df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip',
                                   quoting=csv.QUOTE_NONE, sep=',')
            except UnicodeDecodeError:
                logger.warning("UTF-8 encoding failed, trying latin-1")
                try:
                    df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip')
                except pd.errors.ParserError:
                    import csv
                    df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip',
                                   quoting=csv.QUOTE_NONE, sep=',')

            logger.info(f"Read {len(df)} rows from companies CSV")

            if df.empty:
                raise CSVValidationError("CSV file is empty")

            # Check required columns
            required_columns = ['company_name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise CSVValidationError(f"Missing required columns: {missing_columns}")

            # Process rows in batches
            valid_companies = []
            total_processed = 0
            total_errors = 0

            for start_idx in range(0, len(df), batch_size):
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]

                batch_companies = []
                for idx, row in batch_df.iterrows():
                    company = self.validate_company_row(row, idx)
                    if company:
                        batch_companies.append(company)
                    else:
                        total_errors += 1

                # Insert batch if we have valid data
                if batch_companies:
                    inserted_count = await self.db_service.batch_create_companies(batch_companies)
                    valid_companies.extend(batch_companies)
                    logger.info(f"Inserted batch {start_idx//batch_size + 1}: {inserted_count} companies")

                total_processed += len(batch_df)

            result = {
                "total_rows": len(df),
                "processed_rows": total_processed,
                "valid_rows": len(valid_companies),
                "error_rows": total_errors,
                "validation_errors": self.validation_errors[:50],  # Limit error list
                "success": True
            }

            logger.info(f"Companies loading completed: {result}")
            return result

        except Exception as e:
            error_msg = f"Failed to load companies CSV: {e}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "validation_errors": self.validation_errors,
                "success": False
            }

    async def load_all_csvs(self, data_dir: Path) -> Dict[str, Any]:
        """Load both incentives and companies CSVs"""
        incentives_path = data_dir / "incentives.csv"
        companies_path = data_dir / "companies.csv"

        results = {
            "incentives": None,
            "companies": None,
            "overall_success": False
        }

        # Load incentives
        if incentives_path.exists():
            results["incentives"] = await self.load_incentives_csv(incentives_path)
        else:
            logger.warning(f"Incentives CSV not found: {incentives_path}")
            results["incentives"] = {"error": "File not found", "success": False}

        # Load companies
        if companies_path.exists():
            results["companies"] = await self.load_companies_csv(companies_path)
        else:
            logger.warning(f"Companies CSV not found: {companies_path}")
            results["companies"] = {"error": "File not found", "success": False}

        # Overall success
        results["overall_success"] = (
            results["incentives"]["success"] and results["companies"]["success"]
        )

        return results