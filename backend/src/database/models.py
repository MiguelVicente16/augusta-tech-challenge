"""
Backward compatibility layer

Re-exports models and schema for existing imports.
New code should import from:
- src.models import IncentiveModel, CompanyModel, MatchModel
- src.database.schema import FULL_SCHEMA
"""

# Re-export models from top-level src.models
from ..models import IncentiveModel, CompanyModel, MatchModel

# Re-export schema
from .schema import (
    CREATE_INCENTIVES_TABLE,
    CREATE_COMPANIES_TABLE,
    CREATE_MATCHES_TABLE,
    CREATE_INDICES,
    FULL_SCHEMA
)

__all__ = [
    "IncentiveModel",
    "CompanyModel",
    "MatchModel",
    "CREATE_INCENTIVES_TABLE",
    "CREATE_COMPANIES_TABLE",
    "CREATE_MATCHES_TABLE",
    "CREATE_INDICES",
    "FULL_SCHEMA",
]
