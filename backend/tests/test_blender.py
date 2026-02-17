from backend.models.valuations import CompsResult, DCFResult, LastRoundResult
from backend.valuation.blender import compute_blended_valuation


def _comps(ev: float, count: int = 3) -> CompsResult:
    return CompsResult(
        enterprise_value=ev,
        ev_to_revenue_median=5.0,
        ev_to_revenue_mean=5.0,
        comparable_count=count,
        comparables_used=["A"] * count,
    )


def _dcf(ev: float) -> DCFResult:
    return DCFResult(
        enterprise_value=ev,
        projected_fcfs=[10, 12, 14],
        terminal_value=100,
        discount_rate=0.12,
        terminal_growth_rate=0.03,
    )


def _last_round(ev: float, months: int = 6) -> LastRoundResult:
    return LastRoundResult(
        enterprise_value=ev,
        last_round_valuation=ev,
        adjustment_factor=1.0,
        months_since_round=months,
    )


def test_all_three_methods():
    result = compute_blended_valuation(_comps(100), _dcf(120), _last_round(110))
    assert result.fair_value > 0
    assert len(result.methodology_weights) == 3
    total_weight = sum(w.weight for w in result.methodology_weights)
    assert abs(total_weight - 1.0) < 0.001


def test_comps_only():
    result = compute_blended_valuation(comps=_comps(100))
    assert result.fair_value == 100.0
    assert len(result.methodology_weights) == 1


def test_no_results():
    result = compute_blended_valuation()
    assert result.fair_value == 0.0
    assert len(result.methodology_weights) == 0


def test_custom_weights():
    result = compute_blended_valuation(
        _comps(100), _dcf(200), None,
        custom_weights={"comps": 0.6, "dcf": 0.4},
    )
    expected = 100 * 0.6 + 200 * 0.4
    assert abs(result.fair_value - expected) < 0.01


def test_stale_last_round_lower_weight():
    fresh = compute_blended_valuation(_comps(100), _dcf(100), _last_round(100, months=6))
    stale = compute_blended_valuation(_comps(100), _dcf(100), _last_round(100, months=24))

    fresh_lr_weight = next(w for w in fresh.methodology_weights if w.method == "last_round").weight
    stale_lr_weight = next(w for w in stale.methodology_weights if w.method == "last_round").weight
    assert stale_lr_weight < fresh_lr_weight


def test_range_tightens_with_more_comps():
    few = compute_blended_valuation(_comps(100, count=2))
    many = compute_blended_valuation(_comps(100, count=6))
    few_range = few.fair_value_range[1] - few.fair_value_range[0]
    many_range = many.fair_value_range[1] - many.fair_value_range[0]
    assert many_range < few_range


def test_zero_ev_excluded():
    comps = CompsResult(
        enterprise_value=0.0,
        ev_to_revenue_median=0.0,
        ev_to_revenue_mean=0.0,
        comparable_count=0,
    )
    result = compute_blended_valuation(comps=comps, dcf=_dcf(100))
    # comps with 0 EV should be excluded
    methods = [w.method for w in result.methodology_weights]
    assert "comps" not in methods
    assert result.fair_value == 100.0


def test_rationale_contains_comp_count():
    result = compute_blended_valuation(_comps(100, count=4), _dcf(120))
    comps_weight = next(w for w in result.methodology_weights if w.method == "comps")
    assert "comparable_count (4)" in comps_weight.rationale
    assert ">= 3" in comps_weight.rationale


def test_rationale_stale_last_round():
    result = compute_blended_valuation(comps=_comps(100), last_round=_last_round(100, months=24))
    lr_weight = next(w for w in result.methodology_weights if w.method == "last_round")
    assert "24mo ago" in lr_weight.rationale
    assert "staleness" in lr_weight.rationale


def test_rationale_dcf_years():
    result = compute_blended_valuation(dcf=_dcf(100))
    dcf_weight = next(w for w in result.methodology_weights if w.method == "dcf")
    assert "3-year" in dcf_weight.rationale
