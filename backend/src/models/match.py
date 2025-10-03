"""
Pydantic model for matches table (Phase 2)
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MatchModel(BaseModel):
    """Pydantic model for matches table"""

    id: Optional[int] = None
    incentive_id: int
    company_id: int
    score: Decimal = Field(..., ge=0, le=5)
    rank_position: int = Field(..., ge=1, le=5)
    reasoning: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = {
            Decimal: float,
            datetime: lambda v: v.isoformat() if v else None
        }
