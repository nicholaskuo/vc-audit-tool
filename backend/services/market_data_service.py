import asyncio
import os
import logging
from datetime import datetime, timezone

from backend.models.market_data import CompanyFinancials, IndexData

logger = logging.getLogger(__name__)

# Hardcoded mock data for common tickers across sectors
MOCK_FINANCIALS: dict[str, dict] = {
    # Technology
    "MSFT": {"name": "Microsoft", "market_cap": 3_000_000_000_000, "enterprise_value": 2_950_000_000_000, "revenue": 236_000_000_000, "ebitda": 120_000_000_000, "ev_to_revenue": 12.5, "ev_to_ebitda": 24.6, "sector": "Technology"},
    "AAPL": {"name": "Apple", "market_cap": 2_800_000_000_000, "enterprise_value": 2_780_000_000_000, "revenue": 383_000_000_000, "ebitda": 130_000_000_000, "ev_to_revenue": 7.3, "ev_to_ebitda": 21.4, "sector": "Technology"},
    "GOOGL": {"name": "Alphabet", "market_cap": 2_100_000_000_000, "enterprise_value": 2_050_000_000_000, "revenue": 340_000_000_000, "ebitda": 110_000_000_000, "ev_to_revenue": 6.0, "ev_to_ebitda": 18.6, "sector": "Technology"},
    "AMZN": {"name": "Amazon", "market_cap": 1_900_000_000_000, "enterprise_value": 1_920_000_000_000, "revenue": 620_000_000_000, "ebitda": 85_000_000_000, "ev_to_revenue": 3.1, "ev_to_ebitda": 22.6, "sector": "Consumer Cyclical"},
    "META": {"name": "Meta Platforms", "market_cap": 1_500_000_000_000, "enterprise_value": 1_480_000_000_000, "revenue": 160_000_000_000, "ebitda": 65_000_000_000, "ev_to_revenue": 9.3, "ev_to_ebitda": 22.8, "sector": "Technology"},
    "CRM": {"name": "Salesforce", "market_cap": 280_000_000_000, "enterprise_value": 275_000_000_000, "revenue": 35_000_000_000, "ebitda": 10_500_000_000, "ev_to_revenue": 7.9, "ev_to_ebitda": 26.2, "sector": "Technology"},
    "NOW": {"name": "ServiceNow", "market_cap": 175_000_000_000, "enterprise_value": 173_000_000_000, "revenue": 10_500_000_000, "ebitda": 3_000_000_000, "ev_to_revenue": 16.5, "ev_to_ebitda": 57.7, "sector": "Technology"},
    "SNOW": {"name": "Snowflake", "market_cap": 65_000_000_000, "enterprise_value": 62_000_000_000, "revenue": 3_400_000_000, "ebitda": -200_000_000, "ev_to_revenue": 18.2, "ev_to_ebitda": None, "sector": "Technology"},
    "DDOG": {"name": "Datadog", "market_cap": 42_000_000_000, "enterprise_value": 40_000_000_000, "revenue": 2_600_000_000, "ebitda": 500_000_000, "ev_to_revenue": 15.4, "ev_to_ebitda": 80.0, "sector": "Technology"},
    "NET": {"name": "Cloudflare", "market_cap": 35_000_000_000, "enterprise_value": 34_500_000_000, "revenue": 1_700_000_000, "ebitda": 100_000_000, "ev_to_revenue": 20.3, "ev_to_ebitda": 345.0, "sector": "Technology"},
    # Agriculture / Food & Beverage
    "ADM": {"name": "Archer-Daniels-Midland", "market_cap": 25_000_000_000, "enterprise_value": 32_000_000_000, "revenue": 93_000_000_000, "ebitda": 5_200_000_000, "ev_to_revenue": 0.34, "ev_to_ebitda": 6.2, "sector": "Consumer Defensive"},
    "BG": {"name": "Bunge Global", "market_cap": 14_000_000_000, "enterprise_value": 20_000_000_000, "revenue": 56_000_000_000, "ebitda": 3_100_000_000, "ev_to_revenue": 0.36, "ev_to_ebitda": 6.5, "sector": "Consumer Defensive"},
    "INGR": {"name": "Ingredion", "market_cap": 9_000_000_000, "enterprise_value": 11_500_000_000, "revenue": 8_000_000_000, "ebitda": 1_400_000_000, "ev_to_revenue": 1.44, "ev_to_ebitda": 8.2, "sector": "Consumer Defensive"},
    "TSN": {"name": "Tyson Foods", "market_cap": 22_000_000_000, "enterprise_value": 32_000_000_000, "revenue": 53_000_000_000, "ebitda": 3_600_000_000, "ev_to_revenue": 0.60, "ev_to_ebitda": 8.9, "sector": "Consumer Defensive"},
    # Healthcare / Pharma
    "JNJ": {"name": "Johnson & Johnson", "market_cap": 380_000_000_000, "enterprise_value": 395_000_000_000, "revenue": 85_000_000_000, "ebitda": 30_000_000_000, "ev_to_revenue": 4.6, "ev_to_ebitda": 13.2, "sector": "Healthcare"},
    "UNH": {"name": "UnitedHealth Group", "market_cap": 450_000_000_000, "enterprise_value": 500_000_000_000, "revenue": 372_000_000_000, "ebitda": 36_000_000_000, "ev_to_revenue": 1.3, "ev_to_ebitda": 13.9, "sector": "Healthcare"},
    # Financial Services
    "JPM": {"name": "JPMorgan Chase", "market_cap": 580_000_000_000, "enterprise_value": 580_000_000_000, "revenue": 158_000_000_000, "ebitda": 65_000_000_000, "ev_to_revenue": 3.7, "ev_to_ebitda": 8.9, "sector": "Financial Services"},
    "GS": {"name": "Goldman Sachs", "market_cap": 150_000_000_000, "enterprise_value": 150_000_000_000, "revenue": 47_000_000_000, "ebitda": 15_000_000_000, "ev_to_revenue": 3.2, "ev_to_ebitda": 10.0, "sector": "Financial Services"},
    # Industrials / Energy
    "CAT": {"name": "Caterpillar", "market_cap": 180_000_000_000, "enterprise_value": 200_000_000_000, "revenue": 67_000_000_000, "ebitda": 16_000_000_000, "ev_to_revenue": 3.0, "ev_to_ebitda": 12.5, "sector": "Industrials"},
    "DE": {"name": "Deere & Company", "market_cap": 120_000_000_000, "enterprise_value": 155_000_000_000, "revenue": 55_000_000_000, "ebitda": 12_000_000_000, "ev_to_revenue": 2.8, "ev_to_ebitda": 12.9, "sector": "Industrials"},
}


class MarketDataService:
    def __init__(self):
        self.use_mock = os.getenv("MOCK_MARKET_DATA", "false").lower() == "true"

    async def fetch_comparable_data(self, tickers: list[str]) -> list[CompanyFinancials]:
        results = []
        for ticker in tickers:
            data = await self._fetch_single_ticker(ticker)
            if data:
                results.append(data)
        return results

    async def _fetch_single_ticker(self, ticker: str) -> CompanyFinancials | None:
        if not self.use_mock:
            try:
                return await asyncio.to_thread(self._fetch_yfinance, ticker)
            except Exception as e:
                logger.warning(f"yfinance failed for {ticker}: {e}, falling back to mock")

        return self._get_mock_data(ticker)

    def _fetch_yfinance(self, ticker: str) -> CompanyFinancials:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}

        market_cap = info.get("marketCap")
        enterprise_value = info.get("enterpriseValue")
        revenue = info.get("totalRevenue")
        ebitda = info.get("ebitda")

        ev_to_rev = None
        if enterprise_value and revenue and revenue > 0:
            ev_to_rev = enterprise_value / revenue

        ev_to_ebitda = None
        if enterprise_value and ebitda and ebitda > 0:
            ev_to_ebitda = enterprise_value / ebitda

        return CompanyFinancials(
            ticker=ticker,
            name=info.get("shortName"),
            market_cap=market_cap,
            enterprise_value=enterprise_value,
            revenue=revenue,
            ebitda=ebitda,
            ev_to_revenue=ev_to_rev,
            ev_to_ebitda=ev_to_ebitda,
            sector=info.get("sector"),
            data_source_url=f"https://finance.yahoo.com/quote/{ticker}",
            fetched_at=datetime.now(timezone.utc),
            data_source="live_yfinance",
        )

    def _get_mock_data(self, ticker: str) -> CompanyFinancials | None:
        upper = ticker.upper()
        if upper in MOCK_FINANCIALS:
            d = MOCK_FINANCIALS[upper]
            return CompanyFinancials(
                ticker=upper,
                **d,
                data_source_url=f"https://finance.yahoo.com/quote/{upper}",
                fetched_at=datetime.now(timezone.utc),
                data_source="mock",
            )
        logger.warning(f"No mock data for {ticker}")
        return None

    async def fetch_index_data(self, index_ticker: str, round_date: str) -> IndexData | None:
        if not self.use_mock:
            try:
                return await asyncio.to_thread(self._fetch_index_yfinance, index_ticker, round_date)
            except Exception as e:
                logger.warning(f"yfinance index fetch failed: {e}, falling back to mock")

        return self._get_mock_index(index_ticker, round_date)

    def _fetch_index_yfinance(self, index_ticker: str, round_date: str) -> IndexData | None:
        import yfinance as yf

        rd = datetime.strptime(round_date, "%Y-%m-%d")
        hist = yf.download(index_ticker, start=rd.strftime("%Y-%m-%d"), progress=False)
        if hist.empty:
            return None

        price_at_round = float(hist.iloc[0]["Close"])
        price_current = float(hist.iloc[-1]["Close"])
        ret = (price_current - price_at_round) / price_at_round if price_at_round > 0 else None

        return IndexData(
            ticker=index_ticker,
            price_at_round=price_at_round,
            price_current=price_current,
            return_since_round=ret,
        )

    def _get_mock_index(self, index_ticker: str, round_date: str) -> IndexData | None:
        # Simulate reasonable index return based on approximate date
        try:
            rd = datetime.strptime(round_date, "%Y-%m-%d")
            months = (datetime.now(timezone.utc).replace(tzinfo=None) - rd).days / 30
            annual_return = 0.12  # ~12% annual for NASDAQ
            ret = annual_return * (months / 12)
            return IndexData(
                ticker=index_ticker,
                price_at_round=14000.0,
                price_current=14000.0 * (1 + ret),
                return_since_round=ret,
            )
        except (ValueError, TypeError):
            return None
