from backend.models.market_data import CompanyFinancials
from backend.valuation.comps import compute_comps_valuation, score_and_filter_comps, _sectors_related


def _make_comp(
    ticker: str,
    ev_rev: float | None,
    ev_ebitda: float | None = None,
    sector: str | None = None,
    revenue: float | None = None,
    market_cap: float | None = None,
    enterprise_value: float | None = None,
    ebitda: float | None = None,
) -> CompanyFinancials:
    return CompanyFinancials(
        ticker=ticker,
        ev_to_revenue=ev_rev,
        ev_to_ebitda=ev_ebitda,
        sector=sector,
        revenue=revenue,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        ebitda=ebitda,
    )


def test_basic_comps():
    comps = [_make_comp("A", 5.0), _make_comp("B", 7.0), _make_comp("C", 6.0)]
    result = compute_comps_valuation(100.0, None, comps)
    assert result.comparable_count == 3
    assert result.ev_to_revenue_median == 6.0
    assert result.enterprise_value == 600.0
    assert not result.warnings


def test_single_comp_warns():
    comps = [_make_comp("A", 5.0)]
    result = compute_comps_valuation(100.0, None, comps)
    assert result.comparable_count == 1
    assert result.enterprise_value == 500.0
    assert any("Only 1" in w for w in result.warnings)


def test_no_valid_comps():
    comps = [_make_comp("A", None), _make_comp("B", None)]
    result = compute_comps_valuation(100.0, None, comps)
    assert result.comparable_count == 0
    assert result.enterprise_value == 0.0
    assert any("No valid" in w for w in result.warnings)


def test_empty_comps():
    result = compute_comps_valuation(100.0, None, [])
    assert result.comparable_count == 0
    assert result.enterprise_value == 0.0


def test_ebitda_multiples():
    comps = [
        _make_comp("A", 5.0, 10.0),
        _make_comp("B", 7.0, 12.0),
    ]
    result = compute_comps_valuation(100.0, 50.0, comps)
    assert result.ev_to_ebitda_median is not None
    assert result.ev_to_ebitda_median == 11.0


def test_filters_zero_multiples():
    comps = [_make_comp("A", 0.0), _make_comp("B", 5.0), _make_comp("C", 6.0)]
    result = compute_comps_valuation(100.0, None, comps)
    assert result.comparable_count == 2
    assert "A" not in result.comparables_used


# --- Scoring tests ---

def test_sector_scoring():
    assert _sectors_related("Technology", "Technology") == 1.0
    assert _sectors_related("Technology", "Software") == 0.5
    assert _sectors_related("Technology", "Healthcare") == 0.0
    assert _sectors_related(None, "Technology") == 0.5


def test_size_filtering():
    """Comps outside 0.1x-10x revenue range should be excluded."""
    comps = [
        _make_comp("BIG", 10.0, sector="Technology", revenue=1_000_000_000, market_cap=10e9, enterprise_value=10e9),
        _make_comp("MATCH", 8.0, sector="Technology", revenue=50_000_000, market_cap=400e6, enterprise_value=400e6),
    ]
    included, scores = score_and_filter_comps(comps, target_revenue=50_000_000, target_sector="Technology")
    big_score = next(s for s in scores if s.ticker == "BIG")
    assert big_score.size_proximity_score == 0.0
    assert not big_score.included


def test_selection_scores_populated():
    """When sector is provided, selection_scores should be populated."""
    comps = [
        _make_comp("A", 5.0, sector="Technology", revenue=100e6, market_cap=500e6, enterprise_value=500e6),
        _make_comp("B", 7.0, sector="Technology", revenue=80e6, market_cap=560e6, enterprise_value=560e6),
    ]
    result = compute_comps_valuation(100e6, None, comps, target_sector="Technology")
    assert len(result.comp_selection_scores) == 2
    assert result.selection_criteria.get("target_sector") == "Technology"


def test_excluded_comp_has_reason():
    """Excluded comps must have an exclusion_reason."""
    comps = [
        _make_comp("NODATA", None, sector="Technology"),
    ]
    _, scores = score_and_filter_comps(comps, target_revenue=50e6, target_sector="Technology")
    assert len(scores) == 1
    assert not scores[0].included
    assert scores[0].exclusion_reason is not None
