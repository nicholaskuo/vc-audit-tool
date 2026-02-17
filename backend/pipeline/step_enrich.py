import json
import re
import logging
from backend.models.request import ValuationRequest
from backend.models.enriched import EnrichedInput, EstimatedFinancials
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _parse_research_sources(research_text: str) -> list[dict]:
    """Extract structured [{title, url}] sources from the '--- Sources ---' section."""
    sources: list[dict] = []
    seen_urls: set[str] = set()
    marker = "--- Sources ---"
    idx = research_text.find(marker)
    if idx == -1:
        return sources
    source_block = research_text[idx + len(marker):]
    for line in source_block.strip().splitlines():
        line = line.strip().lstrip("- ")
        if not line:
            continue
        # Format: "Title: https://..."
        match = re.match(r"^(.+?):\s*(https?://\S+)", line)
        if match:
            url = match.group(2).strip()
            if url not in seen_urls:
                seen_urls.add(url)
                sources.append({"title": match.group(1).strip(), "url": url})
    return sources


async def enrich_input(request: ValuationRequest, llm: LLMService) -> EnrichedInput:
    """Step 2: Research the company via web search, then structure the results."""
    needs_research = (
        request.revenue is None
        or request.ebitda is None
        or not request.comparable_tickers
        or request.financial_projections is None
        or request.last_round_valuation is None
    )

    research_context = ""
    research_sources: list[dict] = []
    if needs_research:
        research_context = await _research_company(request, llm)
        research_sources = _parse_research_sources(research_context)
        logger.info(
            f"Research completed for '{request.company_name}': "
            f"{len(research_context)} chars, {len(research_sources)} sources"
        )

    result = await _structure_enrichment(request, research_context, llm)

    # Attach parsed research sources (independent of LLM structured output)
    if research_sources:
        result.research_sources = research_sources

    return result


async def _research_company(request: ValuationRequest, llm: LLMService) -> str:
    """Phase 1: Use web search to find real financial data about the company."""
    search_prompt = (
        f"Research the company \"{request.company_name}\" for a financial valuation.\n\n"
    )

    if request.description:
        search_prompt += f"Company description: {request.description}\n"
    if request.sector:
        search_prompt += f"Sector: {request.sector}\n"

    search_prompt += (
        "\nI need the following information:\n"
        "1. **Annual Revenue** (most recent, in USD)\n"
        "2. **EBITDA** (most recent, in USD)\n"
        "3. **Enterprise Value** (if available)\n"
        "4. **Industry/Sector** classification\n"
        "5. **Comparable public companies** (3-5 tickers of similar companies)\n"
        "6. **Key business metrics** (growth rate, margins, etc.)\n"
        "7. **Last funding round info** (valuation, date, investors, round type — e.g., Series B at $500M in 2023)\n"
        "8. **Revenue growth trajectory** (historical growth rates, projected growth if available)\n\n"
        "If this is a private company, search for any publicly available financial data, "
        "funding rounds, press releases, or industry reports that mention revenue or valuation. "
        "If no exact data is found, find data on similar companies in the same space to "
        "establish reasonable estimates.\n\n"
        "Be specific with numbers and cite your sources."
    )

    return await llm.research_completion(
        prompt=search_prompt,
        step_name="research",
    )


async def _structure_enrichment(
    request: ValuationRequest,
    research_context: str,
    llm: LLMService,
) -> EnrichedInput:
    """Phase 2: Parse research results into structured EnrichedInput."""
    system_prompt = (
        "You are a senior financial analyst. Based on the company information and research "
        "provided, produce a structured analysis.\n\n"
        "Rules:\n"
        "- For 'comparable_tickers': suggest 3-5 public company tickers that are genuine peers.\n"
        "- For 'applicable_methods': always include 'comps' if revenue data exists or was found "
        "in research. Include 'dcf' if the user provided financial_projections OR if you can estimate "
        "projections from research (growth rates, margins). Include 'last_round' "
        "if last round data was provided by the user OR if you can estimate it from research.\n"
        "- For 'estimated_financials': CRITICAL — you MUST populate this whenever "
        "user_provided_revenue is null or user_provided_ebitda is null AND the research "
        "mentions ANY revenue or EBITDA figures. The downstream pipeline CANNOT run comps "
        "or DCF without estimated_financials.estimated_revenue. Even for well-known public "
        "companies, you must extract the revenue/EBITDA numbers into this field. "
        "Set estimated_revenue to the annual revenue in USD (e.g., 674540000000 for $674.54B). "
        "Set estimated_ebitda to the annual EBITDA in USD. "
        "Set revenue_source to describe where the data came from (e.g., 'web search - company press release', "
        "'web search - industry estimate', 'inferred from comparable companies'). "
        "Set confidence to 'high' if from a reliable source, 'medium' if from indirect sources, "
        "'low' if heavily estimated.\n"
        "- For 'estimated_projections': populate this if the user did NOT provide financial_projections "
        "and the research found enough data to estimate growth rates and EBITDA margins. "
        "Provide 5 years of rates. Use estimated_wacc and estimated_terminal_growth_rate "
        "appropriate for the company's risk profile and sector. Include source and reasoning.\n"
        "- For 'estimated_last_round': populate this if the user did NOT provide last round data "
        "and the research found funding round information. Set estimated_valuation to the round's "
        "post-money valuation and estimated_date to the round date (YYYY-MM-DD format). "
        "Include source and reasoning. Only populate if you have reasonably specific data.\n"
        "- For 'enrichment_notes': provide your full reasoning chain.\n"
        "- For 'reasoning' in estimated_financials: explain exactly how you arrived at the numbers "
        "and what sources informed the estimate."
    )

    user_data = {
        "company_name": request.company_name,
        "description": request.description,
        "sector": request.sector,
        "user_provided_revenue": request.revenue,
        "user_provided_ebitda": request.ebitda,
        "user_suggested_comps": request.comparable_tickers,
        "has_projections": request.financial_projections is not None,
        "has_last_round": request.last_round_valuation is not None and request.last_round_date is not None,
    }

    user_prompt = f"Company data:\n{json.dumps(user_data, indent=2)}"

    if research_context:
        user_prompt += f"\n\n--- Web Research Results ---\n{research_context}"

    result = await llm.structured_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_model=EnrichedInput,
        step_name="enrich",
    )

    # Fallback: if LLM didn't populate estimated_financials but research has data
    if (
        result.estimated_financials is None
        and request.revenue is None
        and research_context
    ):
        extracted = _extract_financials_from_research(research_context)
        if extracted:
            result.estimated_financials = extracted
            logger.info(
                f"Fallback extraction: revenue=${extracted.estimated_revenue:,.0f}"
                if extracted.estimated_revenue
                else "Fallback extraction: no revenue found"
            )

    # Ensure comps is in applicable methods if we have revenue from any source
    has_revenue = request.revenue is not None
    has_estimated_revenue = (
        result.estimated_financials is not None
        and result.estimated_financials.estimated_revenue is not None
        and result.estimated_financials.estimated_revenue > 0
    )
    if (has_revenue or has_estimated_revenue) and "comps" not in result.applicable_methods:
        result.applicable_methods.append("comps")

    # Remove DCF only if user didn't provide projections AND we couldn't estimate them
    if request.financial_projections is None and "dcf" in result.applicable_methods:
        has_estimated = (
            result.estimated_projections is not None
            and len(result.estimated_projections.estimated_growth_rates) > 0
        )
        if not has_estimated:
            result.applicable_methods.remove("dcf")
            logger.info("Removed 'dcf' from applicable methods — no user projections and no estimated projections")

    # Ensure last_round is in applicable methods if we have estimated last round
    if (request.last_round_valuation is None or request.last_round_date is None) and result.estimated_last_round is not None:
        elr = result.estimated_last_round
        if elr.estimated_valuation > 0 and elr.estimated_date and "last_round" not in result.applicable_methods:
            result.applicable_methods.append("last_round")
            logger.info("Added 'last_round' to applicable methods based on estimated last round data")

    # Force confidence to "low" on all model-estimated values — the LLM
    # sometimes reports "medium" or "high" but everything it estimates from
    # web research should be treated as low confidence for audit purposes.
    if result.estimated_projections is not None:
        result.estimated_projections.confidence = "low"
    if result.estimated_last_round is not None:
        result.estimated_last_round.confidence = "low"

    logger.info(
        f"Enrichment structured: sector={result.sector}, "
        f"comps={result.comparable_tickers}, methods={result.applicable_methods}, "
        f"estimated_revenue={result.estimated_financials.estimated_revenue if result.estimated_financials else 'N/A'}"
    )

    return result


def _extract_financials_from_research(research_text: str) -> EstimatedFinancials | None:
    """Fallback: extract revenue/EBITDA from research text using pattern matching."""
    multipliers = {"trillion": 1e12, "billion": 1e9, "million": 1e6}

    def _first_dollar(text: str) -> float | None:
        m = re.search(r'\$\s*([\d,.]+)\s*(trillion|billion|million)', text, re.IGNORECASE)
        if not m:
            return None
        return float(m.group(1).replace(',', '')) * multipliers[m.group(2).lower()]

    revenue = None
    ebitda = None

    # Split on newlines (avoid splitting on dots which break "$674.54")
    segments = research_text.split('\n')
    for seg in segments:
        seg_lower = seg.lower()
        if revenue is None and any(kw in seg_lower for kw in ['revenue', 'net sales', 'total sales']):
            # Skip "revenue growth" / "revenue source" lines
            if not any(skip in seg_lower for skip in ['growth rate', 'revenue source']):
                revenue = _first_dollar(seg)
        if ebitda is None and 'ebitda' in seg_lower:
            if 'margin' not in seg_lower and 'multiple' not in seg_lower:
                ebitda = _first_dollar(seg)

    if revenue is None and ebitda is None:
        return None

    parts = []
    if revenue:
        parts.append(f"Revenue: ${revenue:,.0f}")
    if ebitda:
        parts.append(f"EBITDA: ${ebitda:,.0f}")

    return EstimatedFinancials(
        estimated_revenue=revenue,
        estimated_ebitda=ebitda,
        revenue_source="web search - extracted from research text (fallback)",
        confidence="medium",
        reasoning=f"Extracted from web research results. {', '.join(parts)}",
    )


def fallback_enrich(request: ValuationRequest) -> EnrichedInput:
    """Fallback if LLM enrichment fails — use raw user inputs."""
    methods = []
    if request.revenue:
        methods.append("comps")
    if request.financial_projections:
        methods.append("dcf")
    if request.last_round_valuation and request.last_round_date:
        methods.append("last_round")

    return EnrichedInput(
        sector=request.sector or "Unknown",
        comparable_tickers=request.comparable_tickers or [],
        applicable_methods=methods if methods else ["comps"],
        enrichment_notes="Fallback: LLM enrichment unavailable, using raw inputs",
    )
