import time
import uuid
import logging
from datetime import datetime, timezone

from backend.models.request import ValuationRequest
from backend.models.enriched import EnrichedInput
from backend.models.market_data import MarketData
from backend.models.valuations import BlendedValuation
from backend.models.report import PipelineStep, ValuationReport
from backend.services.llm_service import LLMService
from backend.services.market_data_service import MarketDataService
from backend.services.db_service import DBService
from backend.services.pipeline_status import PipelineStatus
from backend.pipeline.step_enrich import enrich_input, fallback_enrich
from backend.pipeline.step_fetch import fetch_market_data
from backend.pipeline.step_valuate import run_valuations, InsufficientDataError
from backend.pipeline.step_narrate import generate_narrative, fallback_narrative
from backend.pipeline.step_persist import persist_report

logger = logging.getLogger(__name__)


class ValuationPipeline:
    def __init__(self, llm: LLMService, market: MarketDataService, db: DBService):
        self.llm = llm
        self.market = market
        self.db = db

    async def run(
        self,
        request: ValuationRequest,
        report_id: str | None = None,
        status: PipelineStatus | None = None,
    ) -> ValuationReport:
        if report_id is None:
            report_id = str(uuid.uuid4())
        steps: list[PipelineStep] = []
        self.llm.call_logs = []  # reset for this run

        logger.info(f"=== Pipeline started for '{request.company_name}' (id={report_id}) ===")

        # Build assumptions dict
        assumptions: dict = {
            "company_name": request.company_name,
            "revenue": request.revenue,
            "revenue_source": "user-provided" if request.revenue else "not provided",
            "ebitda": request.ebitda,
        }
        if request.financial_projections:
            assumptions["wacc"] = request.financial_projections.wacc
            assumptions["terminal_growth_rate"] = request.financial_projections.terminal_growth_rate
            assumptions["tax_rate"] = request.financial_projections.tax_rate
            assumptions["capex_percent"] = request.financial_projections.capex_percent
        if request.last_round_valuation:
            assumptions["last_round_valuation"] = request.last_round_valuation
            assumptions["last_round_date"] = request.last_round_date

        # Step 1: Validate (trivial — Pydantic already did it)
        steps.append(PipelineStep(
            step_name="validate", status="completed",
            started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
            duration_ms=0,
        ))
        if status:
            status.emit("validate", "completed", duration_ms=0)

        # Step 2: Enrich
        enriched = await self._run_step("enrich", steps, self._enrich, request, status=status)

        # Track research sources in assumptions
        if enriched and enriched.research_sources:
            assumptions["research_sources"] = enriched.research_sources

        # Track enriched estimates in assumptions
        if enriched and enriched.estimated_financials:
            ef = enriched.estimated_financials
            if ef.estimated_revenue:
                assumptions["estimated_revenue"] = ef.estimated_revenue
                assumptions["revenue_confidence"] = ef.confidence
                assumptions["revenue_reasoning"] = ef.reasoning
                if request.revenue is None:
                    assumptions["revenue"] = ef.estimated_revenue
                    assumptions["revenue_source"] = f"LLM estimate ({ef.confidence or 'unknown'} confidence)"
            if ef.estimated_ebitda:
                assumptions["estimated_ebitda"] = ef.estimated_ebitda
                if request.ebitda is None:
                    assumptions["ebitda"] = ef.estimated_ebitda

        if enriched and enriched.estimated_projections:
            ep = enriched.estimated_projections
            if ep.estimated_growth_rates:
                assumptions["estimated_growth_rates"] = ep.estimated_growth_rates
                assumptions["estimated_ebitda_margins"] = ep.estimated_ebitda_margins
                assumptions["estimated_wacc"] = ep.estimated_wacc
                assumptions["estimated_terminal_growth_rate"] = ep.estimated_terminal_growth_rate
                assumptions["projections_source"] = ep.source
                assumptions["projections_confidence"] = ep.confidence
                assumptions["projections_reasoning"] = ep.reasoning

        if enriched and enriched.estimated_last_round:
            elr = enriched.estimated_last_round
            if elr.estimated_valuation > 0:
                assumptions["estimated_last_round_valuation"] = elr.estimated_valuation
                assumptions["estimated_last_round_date"] = elr.estimated_date
                assumptions["last_round_source"] = elr.source
                assumptions["last_round_confidence"] = elr.confidence
                assumptions["last_round_reasoning"] = elr.reasoning

        # Step 3: Fetch
        market_data = await self._run_step(
            "fetch", steps, self._fetch, enriched, request, status=status
        )

        # Step 4: Valuate — handle InsufficientDataError explicitly
        blended = None
        error_message = None
        missing_data: list[str] = []

        if status:
            status.emit("valuate", "started")
        valuate_step = PipelineStep(step_name="valuate", status="running", started_at=datetime.now(timezone.utc))
        valuate_start = time.time()
        try:
            blended = self._valuate(request, enriched, market_data)
            valuate_step.status = "completed"
            valuate_step.completed_at = datetime.now(timezone.utc)
            valuate_step.duration_ms = (time.time() - valuate_start) * 1000
            logger.info(f"Step 'valuate' completed in {valuate_step.duration_ms:.0f}ms")
            if status:
                status.emit("valuate", "completed", duration_ms=valuate_step.duration_ms)
        except InsufficientDataError as e:
            valuate_step.status = "failed"
            valuate_step.error = str(e)
            valuate_step.completed_at = datetime.now(timezone.utc)
            valuate_step.duration_ms = (time.time() - valuate_start) * 1000
            error_message = str(e)
            missing_data = e.missing_fields
            logger.error(f"Valuation failed — insufficient data: {e}")
            if status:
                status.emit("valuate", "failed", duration_ms=valuate_step.duration_ms, error=str(e))
        except Exception as e:
            valuate_step.status = "failed"
            valuate_step.error = str(e)
            valuate_step.completed_at = datetime.now(timezone.utc)
            valuate_step.duration_ms = (time.time() - valuate_start) * 1000
            error_message = f"Valuation step encountered an unexpected error: {e}"
            logger.error(f"Step 'valuate' failed: {e}")
            if status:
                status.emit("valuate", "failed", duration_ms=valuate_step.duration_ms, error=str(e))
        steps.append(valuate_step)

        # Step 5: Narrate (skip if valuation failed)
        narrative = None
        if blended and blended.fair_value > 0:
            narrative = await self._run_step(
                "narrate", steps, self._narrate, request, blended, assumptions, status=status
            )
        else:
            steps.append(PipelineStep(
                step_name="narrate", status="skipped",
                started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
                duration_ms=0, error="Skipped — no valuation results to narrate",
            ))
            if status:
                status.emit("narrate", "skipped")

        # Build report
        market_summary = None
        if market_data:
            market_summary = {
                "comparables_count": len(market_data.comparables),
                "comparables": [c.model_dump() for c in market_data.comparables],
                "index_data": market_data.index_data.model_dump() if market_data.index_data else None,
            }

        report = ValuationReport(
            id=report_id,
            company_name=request.company_name,
            request_summary=request.model_dump(),
            enriched_input=enriched.model_dump() if enriched else None,
            market_data_summary=market_summary,
            blended_valuation=blended.model_dump() if blended else None,
            narrative=narrative,
            error=error_message,
            missing_data=missing_data,
            pipeline_steps=steps,
            llm_call_logs=list(self.llm.call_logs),
            created_at=datetime.now(timezone.utc),
            assumptions=assumptions,
        )

        # Step 6: Persist (always persist, even failures, for audit trail)
        await self._run_step("persist", steps, self._persist, report, status=status)

        if status:
            status.mark_complete()

        logger.info(
            f"=== Pipeline completed for '{request.company_name}': "
            f"fair_value={blended.fair_value if blended else 'FAILED'} ==="
        )

        return report

    async def _run_step(self, name: str, steps: list[PipelineStep], fn, *args, status: PipelineStatus | None = None):
        step = PipelineStep(step_name=name, status="running", started_at=datetime.now(timezone.utc))
        start = time.time()
        logger.info(f"Step '{name}' started")
        if status:
            status.emit(name, "started")
        try:
            result = await fn(*args) if _is_coroutine(fn) else fn(*args)
            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc)
            step.duration_ms = (time.time() - start) * 1000
            steps.append(step)
            logger.info(f"Step '{name}' completed in {step.duration_ms:.0f}ms")
            if status:
                status.emit(name, "completed", duration_ms=step.duration_ms)
            return result
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now(timezone.utc)
            step.duration_ms = (time.time() - start) * 1000
            steps.append(step)
            logger.error(f"Step '{name}' failed in {step.duration_ms:.0f}ms: {e}")
            if status:
                status.emit(name, "failed", duration_ms=step.duration_ms, error=str(e))
            return None

    async def _enrich(self, request: ValuationRequest) -> EnrichedInput:
        try:
            return await enrich_input(request, self.llm)
        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}, using fallback")
            return fallback_enrich(request)

    async def _fetch(self, enriched: EnrichedInput | None, request: ValuationRequest) -> MarketData:
        if not enriched:
            enriched = fallback_enrich(request)
        return await fetch_market_data(
            enriched,
            index_ticker=request.index_ticker,
            last_round_date=request.last_round_date,
            market_service=self.market,
        )

    def _valuate(
        self, request: ValuationRequest,
        enriched: EnrichedInput | None,
        market_data: MarketData | None,
    ) -> BlendedValuation:
        if not enriched:
            enriched = fallback_enrich(request)
        if not market_data:
            market_data = MarketData()
        return run_valuations(request, enriched, market_data)

    async def _narrate(
        self, request: ValuationRequest, blended: BlendedValuation | None, assumptions: dict | None = None
    ) -> str:
        try:
            return await generate_narrative(request, blended, self.llm, assumptions=assumptions)
        except Exception as e:
            logger.warning(f"Narrative generation failed: {e}")
            return fallback_narrative(blended)

    def _persist(self, report: ValuationReport) -> str:
        return persist_report(report, self.db)


def _is_coroutine(fn):
    import inspect
    return inspect.iscoroutinefunction(fn)
