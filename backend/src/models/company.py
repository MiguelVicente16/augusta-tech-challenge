"""
Pydantic model for companies table
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanyModel(BaseModel):
    """Pydantic model for companies table"""

    id: Optional[int] = None
    company_name: str
    cae_primary_label: Optional[str] = None
    trade_description_native: Optional[str] = None
    website: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
