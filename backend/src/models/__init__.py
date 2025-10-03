"""
Pydantic models for the application

Organized by domain:
- Database models (incentive, company, match)
- API models (future: request/response models)
- Agent models (future: agent-specific models)

Import all models from here for convenience.
"""

# Database models
from .incentive import IncentiveModel
from .company import CompanyModel
from .match import MatchModel

__all__ = [
    # Database models
    "IncentiveModel",
    "CompanyModel",
    "MatchModel",

    # Future: Add API models, Agent models, etc.
]
