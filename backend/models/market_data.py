from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CompanyFinancials(BaseModel):
    ticker: str
    name: Optional[str] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    sector: Optional[str] = None
    data_source_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    data_source: Optional[str] = None


class IndexData(BaseModel):
    ticker: str
    price_at_round: Optional[float] = None
    price_current: Optional[float] = None
    return_since_round: Optional[float] = Field(None, description="Percentage return since round date")


class MarketData(BaseModel):
    comparables: list[CompanyFinancials] = Field(default_factory=list)
    index_data: Optional[IndexData] = None
