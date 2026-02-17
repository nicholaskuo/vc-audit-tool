from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class PipelineStep(BaseModel):
    step_name: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class LLMCallLog(BaseModel):
    step_name: str
    model: str
    system_prompt: str
    user_prompt: str
    response: str
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValuationReport(BaseModel):
    id: Optional[str] = None
    company_name: str
    request_summary: dict = Field(default_factory=dict)
    enriched_input: Optional[dict] = None
    market_data_summary: Optional[dict] = None
    blended_valuation: Optional[dict] = None
    narrative: Optional[str] = None
    error: Optional[str] = Field(None, description="Error message if the valuation could not be completed")
    missing_data: list[str] = Field(default_factory=list, description="List of missing data points preventing valuation")
    pipeline_steps: list[PipelineStep] = Field(default_factory=list)
    llm_call_logs: list[LLMCallLog] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assumptions: dict = Field(default_factory=dict)
