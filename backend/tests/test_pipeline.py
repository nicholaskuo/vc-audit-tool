import pytest
from unittest.mock import MagicMock

from backend.models.request import ValuationRequest, FinancialProjections
from backend.models.enriched import EnrichedInput, EstimatedFinancials
from backend.models.market_data import CompanyFinancials, IndexData
from backend.pipeline.orchestrator import ValuationPipeline


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.call_logs = []

    async def mock_research(*args, **kwargs):
        return "Mock research: TestCorp has $50M revenue, $10M EBITDA in SaaS analytics."

    async def mock_structured(*args, **kwargs):
        return EnrichedInput(
            sector="Technology",
            comparable_tickers=["MSFT", "CRM"],
            applicable_methods=["comps", "dcf", "last_round"],
            enrichment_notes="Mock enrichment",
        )

    async def mock_text(*args, **kwargs):
        return "This is a mock valuation narrative."

    llm.research_completion = mock_research
    llm.structured_completion = mock_structured
    llm.text_completion = mock_text
    return llm


@pytest.fixture
def mock_market():
    market = MagicMock()

    async def mock_fetch_comps(tickers):
        return [
            CompanyFinancials(
                ticker="MSFT", ev_to_revenue=12.0, ev_to_ebitda=24.0,
                revenue=100_000_000, enterprise_value=1_200_000_000,
                market_cap=1_300_000_000, sector="Technology",
                data_source="mock", data_source_url="https://finance.yahoo.com/quote/MSFT",
            ),
            CompanyFinancials(
                ticker="CRM", ev_to_revenue=8.0, ev_to_ebitda=26.0,
                revenue=80_000_000, enterprise_value=640_000_000,
                market_cap=700_000_000, sector="Technology",
                data_source="mock", data_source_url="https://finance.yahoo.com/quote/CRM",
            ),
        ]

    async def mock_fetch_index(ticker, date):
        return IndexData(ticker=ticker, price_at_round=14000, price_current=15400, return_since_round=0.10)

    market.fetch_comparable_data = mock_fetch_comps
    market.fetch_index_data = mock_fetch_index
    return market


@pytest.fixture
def mock_db(tmp_path):
    from backend.services.db_service import DBService
    return DBService(f"sqlite:///{tmp_path}/test.db")


@pytest.fixture
def full_request():
    return ValuationRequest(
        company_name="TestCorp",
        description="A SaaS analytics company",
        sector="Technology",
        revenue=50_000_000,
        ebitda=10_000_000,
        comparable_tickers=["MSFT", "CRM"],
        financial_projections=FinancialProjections(
            revenue_projections=[60e6, 72e6, 86e6, 100e6, 115e6],
            ebitda_margins=[0.20, 0.22, 0.24, 0.26, 0.28],
            wacc=0.12,
            terminal_growth_rate=0.03,
        ),
        last_round_valuation=200_000_000,
        last_round_date="2024-06-01",
    )


@pytest.mark.asyncio
async def test_full_pipeline(mock_llm, mock_market, mock_db, full_request):
    pipeline = ValuationPipeline(mock_llm, mock_market, mock_db)
    report = await pipeline.run(full_request)

    assert report.id is not None
    assert report.company_name == "TestCorp"
    assert report.blended_valuation is not None
    assert report.blended_valuation["fair_value"] > 0
    assert report.narrative is not None
    assert len(report.pipeline_steps) >= 5

    loaded = mock_db.get_report(report.id)
    assert loaded is not None
    assert loaded.company_name == "TestCorp"


@pytest.mark.asyncio
async def test_comps_only(mock_llm, mock_market, mock_db):
    """Test with only revenue data — only comps should run."""
    request = ValuationRequest(
        company_name="SimpleComp",
        revenue=30_000_000,
    )

    async def mock_enrich(*args, **kwargs):
        return EnrichedInput(
            sector="Unknown",
            comparable_tickers=["MSFT"],
            applicable_methods=["comps"],
        )

    mock_llm.structured_completion = mock_enrich

    pipeline = ValuationPipeline(mock_llm, mock_market, mock_db)
    report = await pipeline.run(request)

    assert report.blended_valuation is not None
    bv = report.blended_valuation
    assert bv["comps_result"] is not None
    assert bv["dcf_result"] is None
    assert bv["last_round_result"] is None


@pytest.mark.asyncio
async def test_name_only_with_estimated_financials(mock_llm, mock_market, mock_db):
    """Test with only company name — LLM research should estimate revenue."""
    request = ValuationRequest(company_name="Acme Analytics")

    async def mock_research(*args, **kwargs):
        return "Acme Analytics is a mid-stage SaaS company with ~$25M ARR."

    async def mock_enrich(*args, **kwargs):
        return EnrichedInput(
            sector="Technology",
            sub_sector="SaaS / Analytics",
            comparable_tickers=["DDOG", "SNOW"],
            applicable_methods=["comps"],
            estimated_financials=EstimatedFinancials(
                estimated_revenue=25_000_000,
                estimated_ebitda=-2_000_000,
                revenue_source="web search - industry estimate",
                confidence="medium",
                reasoning="Based on web research indicating ~$25M ARR for Acme Analytics.",
            ),
            enrichment_notes="Researched via web search. Estimated revenue from industry reports.",
        )

    mock_llm.research_completion = mock_research
    mock_llm.structured_completion = mock_enrich

    pipeline = ValuationPipeline(mock_llm, mock_market, mock_db)
    report = await pipeline.run(request)

    assert report.blended_valuation is not None
    bv = report.blended_valuation
    # Should have run comps using the estimated revenue
    assert bv["comps_result"] is not None
    assert bv["fair_value"] > 0

    # Assumptions should track the estimate source
    assert report.assumptions["revenue_source"] == "LLM estimate (medium confidence)"
    assert report.assumptions["estimated_revenue"] == 25_000_000
