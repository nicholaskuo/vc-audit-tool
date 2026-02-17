from pydantic import BaseModel, Field
from typing import Optional


class EstimatedFinancials(BaseModel):
    estimated_revenue: Optional[float] = Field(None, description="Estimated annual revenue in USD")
    estimated_ebitda: Optional[float] = Field(None, description="Estimated annual EBITDA in USD")
    revenue_source: Optional[str] = Field(None, description="How revenue was estimated (e.g., 'LLM estimate based on public info', 'user-provided')")
    confidence: Optional[str] = Field(None, description="Confidence level: 'high', 'medium', 'low'")
    reasoning: Optional[str] = Field(None, description="Detailed reasoning for the financial estimates")


class EstimatedProjections(BaseModel):
    estimated_growth_rates: list[float] = Field(default_factory=list, description="Projected revenue growth rates per year, e.g. [0.25, 0.20, 0.18, 0.15, 0.12]")
    estimated_ebitda_margins: list[float] = Field(default_factory=list, description="Projected EBITDA margins per year, e.g. [0.15, 0.18, 0.20, 0.22, 0.24]")
    estimated_wacc: float = Field(0.12, description="Estimated WACC")
    estimated_terminal_growth_rate: float = Field(0.03, description="Estimated terminal growth rate")
    source: str = Field("", description="Source of the projection estimates")
    confidence: str = Field("low", description="Confidence level: 'high', 'medium', 'low'")
    reasoning: str = Field("", description="Detailed reasoning for the projection estimates")


class EstimatedLastRound(BaseModel):
    estimated_valuation: float = Field(0.0, description="Estimated last round valuation in USD")
    estimated_date: str = Field("", description="Estimated date of last funding round (YYYY-MM-DD)")
    source: str = Field("", description="Source of the last round estimate")
    confidence: str = Field("low", description="Confidence level: 'high', 'medium', 'low'")
    reasoning: str = Field("", description="Detailed reasoning for the last round estimate")


class EnrichedInput(BaseModel):
    sector: str = Field(..., description="Inferred or confirmed sector")
    sub_sector: Optional[str] = Field(None, description="More specific sub-sector")
    comparable_tickers: list[str] = Field(..., description="Suggested comparable public company tickers")
    applicable_methods: list[str] = Field(
        ..., description="Which valuation methods to apply: 'comps', 'dcf', 'last_round'"
    )
    estimated_financials: Optional[EstimatedFinancials] = Field(
        None, description="LLM-estimated financials when user did not provide them"
    )
    estimated_projections: Optional[EstimatedProjections] = Field(
        None, description="LLM-estimated DCF projection parameters when user did not provide them"
    )
    estimated_last_round: Optional[EstimatedLastRound] = Field(
        None, description="LLM-estimated last funding round data when user did not provide it"
    )
    research_sources: list[dict] = Field(default_factory=list, description="Primary sources from web research [{title, url}]")
    enrichment_notes: Optional[str] = Field(None, description="LLM reasoning about sector/comp selection")
