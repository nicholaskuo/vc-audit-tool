import json
from backend.models.valuations import BlendedValuation
from backend.models.request import ValuationRequest
from backend.services.llm_service import LLMService


async def generate_narrative(
    request: ValuationRequest,
    blended: BlendedValuation,
    llm: LLMService,
    assumptions: dict | None = None,
) -> str:
    """Step 5: Generate auditor-facing narrative via LLM."""
    system_prompt = (
        "You are a senior valuation analyst writing a fair value assessment narrative "
        "for an auditor reviewing a VC portfolio company. Be precise, reference the data, "
        "and explain the methodology weighting rationale. Write 2-4 paragraphs.\n\n"
        "If any inputs were model-estimated (rather than user-provided), prominently disclose "
        "which values were estimated, the confidence level, and the source. This is critical "
        "for audit transparency."
    )

    data = {
        "company_name": request.company_name,
        "sector": request.sector,
        "blended_fair_value": blended.fair_value,
        "fair_value_range": blended.fair_value_range,
        "methodology_weights": [w.model_dump() for w in blended.methodology_weights],
    }

    if blended.comps_result:
        data["comps"] = {
            "ev": blended.comps_result.enterprise_value,
            "median_multiple": blended.comps_result.ev_to_revenue_median,
            "comp_count": blended.comps_result.comparable_count,
            "warnings": blended.comps_result.warnings,
        }

    if blended.dcf_result:
        data["dcf"] = {
            "ev": blended.dcf_result.enterprise_value,
            "wacc": blended.dcf_result.discount_rate,
            "terminal_growth": blended.dcf_result.terminal_growth_rate,
            "warnings": blended.dcf_result.warnings,
        }

    if blended.last_round_result:
        data["last_round"] = {
            "ev": blended.last_round_result.enterprise_value,
            "adjustment_factor": blended.last_round_result.adjustment_factor,
            "months_since": blended.last_round_result.months_since_round,
            "warnings": blended.last_round_result.warnings,
        }

    if assumptions:
        # Include relevant estimation details for the narrative
        estimation_keys = [
            "revenue_source", "projections_source", "projections_confidence",
            "projections_reasoning", "last_round_source", "last_round_confidence",
            "last_round_reasoning", "estimated_growth_rates", "estimated_ebitda_margins",
            "estimated_wacc", "estimated_terminal_growth_rate",
            "estimated_last_round_valuation", "estimated_last_round_date",
        ]
        estimation_data = {k: v for k, v in assumptions.items() if k in estimation_keys and v is not None}
        if estimation_data:
            data["estimation_details"] = estimation_data

    user_prompt = f"Write a valuation narrative for:\n{json.dumps(data, indent=2)}"

    return await llm.text_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        step_name="narrate",
    )


def fallback_narrative(blended: BlendedValuation) -> str:
    """Fallback narrative if LLM is unavailable."""
    parts = [f"Blended fair value estimate: ${blended.fair_value:,.0f}"]
    parts.append(f"Range: ${blended.fair_value_range[0]:,.0f} - ${blended.fair_value_range[1]:,.0f}")
    for w in blended.methodology_weights:
        parts.append(f"- {w.method}: weight {w.weight:.0%} ({w.rationale})")
    return "\n".join(parts)
