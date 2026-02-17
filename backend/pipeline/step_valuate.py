import logging
from backend.models.request import ValuationRequest, FinancialProjections
from backend.models.enriched import EnrichedInput, EstimatedProjections
from backend.models.market_data import MarketData
from backend.models.valuations import CompsResult, DCFResult, LastRoundResult, BlendedValuation
from backend.valuation.comps import compute_comps_valuation
from backend.valuation.dcf import compute_dcf_valuation
from backend.valuation.last_round import compute_last_round_valuation
from backend.valuation.blender import compute_blended_valuation

logger = logging.getLogger(__name__)


class InsufficientDataError(Exception):
    """Raised when the pipeline cannot produce a valuation due to missing data."""
    def __init__(self, message: str, missing_fields: list[str]):
        self.missing_fields = missing_fields
        super().__init__(message)


def _build_estimated_projections(
    base_revenue: float,
    estimated: EstimatedProjections,
) -> FinancialProjections:
    """Convert estimated growth rates + base revenue into FinancialProjections for DCF."""
    growth_rates = estimated.estimated_growth_rates
    margins = estimated.estimated_ebitda_margins

    # Build revenue projections from growth rates
    revenue_projections: list[float] = []
    rev = base_revenue
    for rate in growth_rates:
        rev = rev * (1 + rate)
        revenue_projections.append(rev)

    # Pad margins to match projection length
    while len(margins) < len(revenue_projections):
        margins.append(margins[-1] if margins else 0.20)

    return FinancialProjections(
        revenue_projections=revenue_projections,
        ebitda_margins=margins[:len(revenue_projections)],
        wacc=estimated.estimated_wacc,
        terminal_growth_rate=estimated.estimated_terminal_growth_rate,
    )


def _check_mismatches(
    request: ValuationRequest,
    enriched: EnrichedInput,
    dcf_result: DCFResult | None,
    last_round_result: LastRoundResult | None,
    source_links: str,
) -> None:
    """Check for mismatches between user-provided inputs and research estimates. Mutates result warnings."""
    # DCF mismatches: user provided projections AND estimated_projections exists
    if (
        request.financial_projections is not None
        and enriched.estimated_projections is not None
        and enriched.estimated_projections.estimated_growth_rates
        and dcf_result is not None
    ):
        ep = enriched.estimated_projections
        user_wacc = request.financial_projections.wacc
        user_tgr = request.financial_projections.terminal_growth_rate

        # WACC difference >= 2pp
        if abs(user_wacc - ep.estimated_wacc) >= 0.02:
            dcf_result.warnings.append(
                f"WACC mismatch: user provided {user_wacc:.1%} vs research estimate "
                f"{ep.estimated_wacc:.1%} (difference: {abs(user_wacc - ep.estimated_wacc):.1%}).{source_links}"
            )

        # TGR difference >= 1pp
        if abs(user_tgr - ep.estimated_terminal_growth_rate) >= 0.01:
            dcf_result.warnings.append(
                f"Terminal growth rate mismatch: user provided {user_tgr:.1%} vs research estimate "
                f"{ep.estimated_terminal_growth_rate:.1%} (difference: {abs(user_tgr - ep.estimated_terminal_growth_rate):.1%}).{source_links}"
            )

        # Average growth rate difference > 20% relative
        if ep.estimated_growth_rates and request.financial_projections.revenue_projections:
            user_revs = request.financial_projections.revenue_projections
            if len(user_revs) >= 2:
                # Compute implied growth rates from user revenue projections
                user_growth_rates = []
                for i in range(1, len(user_revs)):
                    if user_revs[i - 1] > 0:
                        user_growth_rates.append(user_revs[i] / user_revs[i - 1] - 1)
                if user_growth_rates:
                    avg_user = sum(user_growth_rates) / len(user_growth_rates)
                    avg_est = sum(ep.estimated_growth_rates) / len(ep.estimated_growth_rates)
                    if avg_est != 0 and abs(avg_user - avg_est) / abs(avg_est) > 0.20:
                        dcf_result.warnings.append(
                            f"Growth rate mismatch: user implied avg {avg_user:.1%}/yr vs research estimate "
                            f"avg {avg_est:.1%}/yr (>{20}% relative difference).{source_links}"
                        )

    # Last round mismatches: user provided AND estimated exists
    if (
        request.last_round_valuation is not None
        and enriched.estimated_last_round is not None
        and enriched.estimated_last_round.estimated_valuation > 0
        and last_round_result is not None
    ):
        user_val = request.last_round_valuation
        est_val = enriched.estimated_last_round.estimated_valuation
        if est_val > 0 and abs(user_val - est_val) / est_val > 0.30:
            last_round_result.warnings.append(
                f"Last round valuation mismatch: user provided ${user_val:,.0f} vs research estimate "
                f"${est_val:,.0f} (>{30}% relative difference).{source_links}"
            )


def run_valuations(
    request: ValuationRequest,
    enriched: EnrichedInput,
    market_data: MarketData,
) -> BlendedValuation:
    """Step 4: Run each applicable valuation method and blend results."""
    comps_result: CompsResult | None = None
    dcf_result: DCFResult | None = None
    last_round_result: LastRoundResult | None = None

    # Resolve revenue: user-provided takes priority, then LLM estimate
    revenue = request.revenue
    ebitda = request.ebitda
    revenue_source = "user-provided"

    # Build source links string for warnings
    source_links = ""
    if enriched.research_sources:
        source_links = " Sources: " + ", ".join(
            f"{s.get('title', 'Link')} ({s.get('url', '')})" for s in enriched.research_sources[:5]
        )

    if revenue is None and enriched.estimated_financials:
        ef = enriched.estimated_financials
        if ef.estimated_revenue and ef.estimated_revenue > 0:
            revenue = ef.estimated_revenue
            revenue_source = f"LLM estimate ({ef.confidence or 'unknown'} confidence)"
            logger.info(f"Using LLM-estimated revenue: ${revenue:,.0f} ({revenue_source})")
        if ebitda is None and ef.estimated_ebitda:
            ebitda = ef.estimated_ebitda
            logger.info(f"Using LLM-estimated EBITDA: ${ebitda:,.0f}")

    # Resolve last round data: user-provided takes priority, then estimated
    last_round_valuation = request.last_round_valuation
    last_round_date = request.last_round_date
    last_round_is_estimated = False
    if (last_round_valuation is None or last_round_date is None) and enriched.estimated_last_round:
        elr = enriched.estimated_last_round
        if elr.estimated_valuation > 0 and elr.estimated_date:
            last_round_valuation = elr.estimated_valuation
            last_round_date = elr.estimated_date
            last_round_is_estimated = True
            logger.info(
                f"Using LLM-estimated last round: ${elr.estimated_valuation:,.0f} "
                f"on {elr.estimated_date} ({elr.confidence} confidence)"
            )

    # Resolve DCF projections: user-provided takes priority, then estimated
    financial_projections = request.financial_projections
    dcf_is_estimated = False
    if financial_projections is None and enriched.estimated_projections and revenue:
        ep = enriched.estimated_projections
        if ep.estimated_growth_rates:
            financial_projections = _build_estimated_projections(revenue, ep)
            dcf_is_estimated = True
            logger.info(
                f"Using LLM-estimated projections: {len(ep.estimated_growth_rates)}-yr growth rates, "
                f"WACC={ep.estimated_wacc:.1%}, TGR={ep.estimated_terminal_growth_rate:.1%} "
                f"({ep.confidence} confidence)"
            )

    # --- Check what we can actually run ---
    can_run_comps = "comps" in enriched.applicable_methods and revenue and len(market_data.comparables) > 0
    can_run_dcf = "dcf" in enriched.applicable_methods and financial_projections is not None
    can_run_last_round = (
        "last_round" in enriched.applicable_methods
        and last_round_valuation is not None
        and last_round_valuation > 0
        and last_round_date is not None
    )

    if not can_run_comps and not can_run_dcf and not can_run_last_round:
        missing = _identify_missing(request, enriched, revenue, market_data)
        msg = (
            f"Unable to perform valuation for \"{request.company_name}\". "
            f"Comparable Company Analysis could not run.\n\n"
            f"What went wrong:\n"
        )
        for field in missing:
            msg += f"  - {field}\n"
        msg += (
            "\nTo run a valuation, please provide at least:\n"
            "  - Annual Revenue (for Comparable Company Analysis)"
        )
        logger.error(msg)
        raise InsufficientDataError(msg, missing)

    if can_run_comps:
        try:
            comps_result = compute_comps_valuation(
                target_revenue=revenue,
                target_ebitda=ebitda,
                comparables=market_data.comparables,
                target_sector=enriched.sector,
            )
            if comps_result and revenue_source != "user-provided":
                comps_result.warnings.append(f"Revenue source: {revenue_source}.{source_links}")
            logger.info(f"Comps result: EV=${comps_result.enterprise_value:,.0f}, {comps_result.comparable_count} comps")
        except Exception as e:
            logger.error(f"Comps valuation failed: {e}")

    if can_run_dcf:
        try:
            dcf_result = compute_dcf_valuation(financial_projections)
            if dcf_result and dcf_is_estimated:
                ep = enriched.estimated_projections
                dcf_result.warnings.append(
                    f"DCF inputs are model-estimated ({ep.confidence} confidence). "
                    f"Growth rates, margins, WACC, and TGR were inferred from web research. "
                    f"Source: {ep.source}.{source_links}"
                )
            logger.info(f"DCF result: EV=${dcf_result.enterprise_value:,.0f}")
        except Exception as e:
            logger.error(f"DCF valuation failed: {e}")

    if can_run_last_round:
        try:
            last_round_result = compute_last_round_valuation(
                last_valuation=last_round_valuation,
                last_round_date=last_round_date,
                index_data=market_data.index_data,
            )
            if last_round_result and last_round_is_estimated:
                elr = enriched.estimated_last_round
                last_round_result.warnings.append(
                    f"Last round data is model-estimated ({elr.confidence} confidence). "
                    f"Source: {elr.source}.{source_links}"
                )
            logger.info(f"Last round result: EV=${last_round_result.enterprise_value:,.0f}")
        except Exception as e:
            logger.error(f"Last round valuation failed: {e}")

    # Check for mismatches between user inputs and research estimates
    _check_mismatches(request, enriched, dcf_result, last_round_result, source_links)

    blended = compute_blended_valuation(comps_result, dcf_result, last_round_result)

    # Final check: all methods ran but all produced $0
    if blended.fair_value == 0:
        missing = _identify_missing(request, enriched, revenue, market_data)
        raise InsufficientDataError(
            f"All valuation methods produced $0 for \"{request.company_name}\". "
            f"This typically means the input data was insufficient or invalid. "
            f"Please verify the provided financials and try again.",
            missing,
        )

    return blended


def _identify_missing(
    request: ValuationRequest,
    enriched: EnrichedInput,
    resolved_revenue: float | None,
    market_data: MarketData,
) -> list[str]:
    """Build a list of human-readable missing data points for comps (the primary method)."""
    missing: list[str] = []

    llm_failed = enriched.enrichment_notes and "Fallback" in enriched.enrichment_notes

    if not resolved_revenue:
        if llm_failed:
            missing.append(
                "Revenue: No annual revenue provided. Web research could not run because "
                "the LLM service is unavailable (check your OPENAI_API_KEY in backend/.env). "
                "Please enter the company's annual revenue manually."
            )
        else:
            missing.append(
                "Revenue: No annual revenue provided, and web research could not determine it. "
                "Please enter the company's annual revenue."
            )
    if resolved_revenue and len(market_data.comparables) == 0:
        missing.append(
            "Comparable companies: Revenue is available but no comparable company data could be fetched. "
            "Try providing ticker symbols of similar public companies."
        )
    return missing
