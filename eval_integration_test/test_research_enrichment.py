"""
LLM eval tests for the research → enrichment pipeline.

These hit the live OpenAI API (web search + structured output) and verify
that the pipeline can find and structure real financial data for well-known
private companies.

Slow (~10-30s each), costs real API tokens — not for CI.

Run:
    python -m pytest eval_integration_test/ -v -s
"""

import re
import pytest
from backend.models.request import ValuationRequest
from backend.pipeline.step_enrich import enrich_input

TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


def _assert_enriched_basics(result):
    """Shared assertions that apply to every company."""
    # Sector
    assert result.sector, "sector should be a non-empty string"

    # Comparable tickers
    assert len(result.comparable_tickers) >= 1, "should find at least 1 comparable ticker"
    for ticker in result.comparable_tickers:
        assert TICKER_RE.match(ticker), f"ticker '{ticker}' is not valid format (1-5 uppercase letters)"

    # Applicable methods
    assert "comps" in result.applicable_methods, "'comps' should be in applicable_methods"

    # Estimated financials
    assert result.estimated_financials is not None, "estimated_financials should not be None"
    assert result.estimated_financials.revenue_source, "revenue_source should be non-empty"
    assert result.estimated_financials.confidence in (
        "high",
        "medium",
        "low",
    ), f"confidence '{result.estimated_financials.confidence}' not in allowed values"

    # Research sources
    assert len(result.research_sources) >= 1, "should have at least 1 research source"


@pytest.mark.asyncio
async def test_spacex(llm_service):
    """SpaceX: widely reported ~$15.5B revenue, aerospace/defense sector."""
    request = ValuationRequest(
        company_name="SpaceX",
        description="Private aerospace manufacturer and space transportation company",
    )

    result = await enrich_input(request, llm_service)

    _assert_enriched_basics(result)

    # Revenue sanity: known ~$15.5B — allow generous $5B–$50B range
    rev = result.estimated_financials.estimated_revenue
    assert rev is not None, "estimated_revenue should not be None"
    assert 5e9 <= rev <= 50e9, (
        f"SpaceX estimated revenue ${rev:,.0f} outside $5B–$50B range"
    )


@pytest.mark.asyncio
async def test_stripe(llm_service):
    """Stripe: widely reported ~$18-20B revenue, fintech/payments sector."""
    request = ValuationRequest(
        company_name="Stripe",
        description="Online payment processing platform for internet businesses",
        sector="Fintech",
    )

    result = await enrich_input(request, llm_service)

    _assert_enriched_basics(result)

    # Revenue sanity: known ~$18-20B — allow $5B–$40B range
    rev = result.estimated_financials.estimated_revenue
    assert rev is not None, "estimated_revenue should not be None"
    assert 5e9 <= rev <= 40e9, (
        f"Stripe estimated revenue ${rev:,.0f} outside $5B–$40B range"
    )


@pytest.mark.asyncio
async def test_databricks(llm_service):
    """Databricks: widely reported ~$2.4B ARR, enterprise software/data & AI."""
    request = ValuationRequest(
        company_name="Databricks",
        description="Enterprise data and AI platform, unified analytics",
    )

    result = await enrich_input(request, llm_service)

    _assert_enriched_basics(result)

    # Revenue sanity: known ~$2.4B ARR — allow $1B–$10B range
    rev = result.estimated_financials.estimated_revenue
    assert rev is not None, "estimated_revenue should not be None"
    assert 1e9 <= rev <= 10e9, (
        f"Databricks estimated revenue ${rev:,.0f} outside $1B–$10B range"
    )
