from backend.models.market_data import IndexData
from backend.valuation.last_round import compute_last_round_valuation


def test_basic_adjustment():
    index = IndexData(ticker="^IXIC", return_since_round=0.15)
    result = compute_last_round_valuation(100_000_000, "2024-06-01", index)
    assert abs(result.enterprise_value - 115_000_000) < 1.0
    assert result.adjustment_factor == 1.15
    assert result.index_return == 0.15


def test_no_index_data():
    result = compute_last_round_valuation(100_000_000, "2024-06-01", None)
    assert result.enterprise_value == 100_000_000
    assert result.adjustment_factor == 1.0
    assert any("No index data" in w for w in result.warnings)


def test_stale_round():
    index = IndexData(ticker="^IXIC", return_since_round=0.30)
    result = compute_last_round_valuation(100_000_000, "2023-01-01", index)
    assert result.months_since_round is not None
    assert result.months_since_round > 18
    assert any("stale" in w for w in result.warnings)


def test_negative_return():
    index = IndexData(ticker="^IXIC", return_since_round=-0.10)
    result = compute_last_round_valuation(100_000_000, "2024-06-01", index)
    assert result.enterprise_value == 90_000_000


def test_bad_date():
    index = IndexData(ticker="^IXIC", return_since_round=0.05)
    result = compute_last_round_valuation(100_000_000, "not-a-date", index)
    assert result.months_since_round is None
    assert any("Could not parse" in w for w in result.warnings)
