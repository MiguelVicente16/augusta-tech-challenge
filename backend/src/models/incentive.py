"""
Pydantic model for incentives table
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)


class IncentiveModel(BaseModel):
    """Pydantic model for incentives table"""

    id: Optional[int] = None
    incentive_project_id: Optional[str] = None
    project_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    ai_description: Optional[str] = None
    ai_description_structured: Optional[Dict[str, Any]] = None
    eligibility_criteria: Optional[Dict[str, Any]] = None
    document_urls: Optional[Union[List[Any], Dict[str, Any]]] = None
    date_publication: Optional[date] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    total_budget: Optional[Decimal] = None
    source_link: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    @validator('eligibility_criteria', pre=True)
    def parse_eligibility_criteria(cls, v):
        """Parse eligibility criteria JSON string to dict"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in eligibility_criteria: {v}")
                return {}
        return v

    @validator('ai_description_structured', pre=True)
    def parse_ai_description_structured(cls, v):
        """Parse ai_description_structured JSON string to dict"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in ai_description_structured: {v}")
                return {}
        return v

    @validator('document_urls', pre=True)
    def parse_document_urls(cls, v):
        """Parse document_urls JSON string to dict/list"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in document_urls: {v}")
                return None
        # Accept both list and dict formats from CSV
        if isinstance(v, (list, dict)):
            return v
        return v

    class Config:
        orm_mode = True
        json_encoders = {
            Decimal: float,
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }
