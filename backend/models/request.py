from pydantic import BaseModel, Field
from typing import Optional


class FinancialProjections(BaseModel):
    revenue_projections: list[float] = Field(..., description="Projected revenues for each year")
    ebitda_margins: list[float] = Field(..., description="EBITDA margin for each year (0.0-1.0)")
    capex_percent: float = Field(0.05, description="CapEx as percent of revenue")
    nwc_change_percent: float = Field(0.02, description="Net working capital change as percent of revenue")
    tax_rate: float = Field(0.25, description="Corporate tax rate")
    wacc: float = Field(0.12, description="Weighted average cost of capital")
    terminal_growth_rate: float = Field(0.03, description="Long-term growth rate for terminal value")
    depreciation_percent: float = Field(0.0, description="D&A as percent of revenue (0.0 = no D&A tax shield)")


class ValuationRequest(BaseModel):
    company_name: str = Field(..., description="Name of the portfolio company")
    description: Optional[str] = Field(None, description="Brief description of the company")
    sector: Optional[str] = Field(None, description="Industry sector")
    revenue: Optional[float] = Field(None, description="Latest annual revenue")
    ebitda: Optional[float] = Field(None, description="Latest annual EBITDA")
    comparable_tickers: Optional[list[str]] = Field(None, description="User-suggested comparable public tickers")
    financial_projections: Optional[FinancialProjections] = Field(None, description="DCF input projections")
    last_round_valuation: Optional[float] = Field(None, description="Valuation at last funding round")
    last_round_date: Optional[str] = Field(None, description="Date of last funding round (YYYY-MM-DD)")
    index_ticker: Optional[str] = Field("^IXIC", description="Market index ticker for last-round adjustment")
