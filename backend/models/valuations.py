from pydantic import BaseModel, Field
from typing import Optional


class CompSelectionScore(BaseModel):
    ticker: str
    name: Optional[str] = None
    included: bool
    sector_score: float
    size_proximity_score: float
    data_quality_score: float
    composite_score: float
    exclusion_reason: Optional[str] = None


class CompsResult(BaseModel):
    method: str = "comps"
    enterprise_value: float
    ev_to_revenue_median: float
    ev_to_revenue_mean: float
    ev_to_ebitda_median: Optional[float] = None
    ev_to_ebitda_mean: Optional[float] = None
    comparable_count: int
    comparables_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    comp_selection_scores: list[CompSelectionScore] = Field(default_factory=list)
    selection_criteria: dict = Field(default_factory=dict)


class SensitivityCell(BaseModel):
    wacc: float
    terminal_growth_rate: float
    enterprise_value: float


class DCFResult(BaseModel):
    method: str = "dcf"
    enterprise_value: float
    projected_fcfs: list[float]
    terminal_value: float
    discount_rate: float
    terminal_growth_rate: float
    warnings: list[str] = Field(default_factory=list)
    sensitivity_table: list[SensitivityCell] = Field(default_factory=list)


class LastRoundResult(BaseModel):
    method: str = "last_round"
    enterprise_value: float
    last_round_valuation: float
    index_return: Optional[float] = None
    adjustment_factor: float
    months_since_round: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


class MethodologyWeight(BaseModel):
    method: str
    weight: float
    rationale: str


class BlendedValuation(BaseModel):
    fair_value: float
    fair_value_range: list[float] = Field(..., description="[low, high] range estimate")
    methodology_weights: list[MethodologyWeight]
    comps_result: Optional[CompsResult] = None
    dcf_result: Optional[DCFResult] = None
    last_round_result: Optional[LastRoundResult] = None
