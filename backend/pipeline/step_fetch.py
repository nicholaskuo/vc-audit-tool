from backend.models.enriched import EnrichedInput
from backend.models.market_data import MarketData
from backend.services.market_data_service import MarketDataService


async def fetch_market_data(
    enriched: EnrichedInput,
    index_ticker: str | None,
    last_round_date: str | None,
    market_service: MarketDataService,
) -> MarketData:
    """Step 3: Fetch comparable company data and index data."""
    comparables = []
    if enriched.comparable_tickers and "comps" in enriched.applicable_methods:
        comparables = await market_service.fetch_comparable_data(enriched.comparable_tickers)

    # Resolve last_round_date: user-provided takes priority, then estimated
    resolved_last_round_date = last_round_date
    if not resolved_last_round_date and enriched.estimated_last_round:
        resolved_last_round_date = enriched.estimated_last_round.estimated_date or None

    index_data = None
    if "last_round" in enriched.applicable_methods and index_ticker and resolved_last_round_date:
        index_data = await market_service.fetch_index_data(index_ticker, resolved_last_round_date)

    return MarketData(comparables=comparables, index_data=index_data)
