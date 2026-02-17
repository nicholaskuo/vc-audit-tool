from backend.models.valuations import (
    CompsResult, DCFResult, LastRoundResult,
    MethodologyWeight, BlendedValuation,
)


def compute_blended_valuation(
    comps: CompsResult | None = None,
    dcf: DCFResult | None = None,
    last_round: LastRoundResult | None = None,
    custom_weights: dict[str, float] | None = None,
) -> BlendedValuation:
    """Blend multiple valuation methodologies into a single fair value estimate."""
    results: dict[str, float] = {}

    if comps and comps.enterprise_value > 0:
        results["comps"] = comps.enterprise_value

    if dcf and dcf.enterprise_value > 0:
        results["dcf"] = dcf.enterprise_value

    if last_round and last_round.enterprise_value > 0:
        results["last_round"] = last_round.enterprise_value

    if not results:
        return BlendedValuation(
            fair_value=0.0,
            fair_value_range=[0.0, 0.0],
            methodology_weights=[],
            comps_result=comps,
            dcf_result=dcf,
            last_round_result=last_round,
        )

    # Determine weights and rationales
    if custom_weights:
        weights = {k: v for k, v in custom_weights.items() if k in results}
        rationales = {k: f"Custom weight {v:.2f}" for k, v in weights.items()}
    else:
        weights, rationales = _default_weights(comps, dcf, last_round, results)

    # Normalize weights to sum to 1.0
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}

    # Compute blended value
    fair_value = sum(results[method] * weights[method] for method in weights)

    # Compute range as +/- 20% by default, tightened by comp count
    range_pct = 0.20
    if comps and comps.comparable_count >= 5:
        range_pct = 0.15
    fair_value_range = [fair_value * (1 - range_pct), fair_value * (1 + range_pct)]

    methodology_weights = [
        MethodologyWeight(method=method, weight=weights[method], rationale=rationales.get(method, ""))
        for method in weights
    ]

    return BlendedValuation(
        fair_value=fair_value,
        fair_value_range=fair_value_range,
        methodology_weights=methodology_weights,
        comps_result=comps,
        dcf_result=dcf,
        last_round_result=last_round,
    )


def _default_weights(
    comps: CompsResult | None,
    dcf: DCFResult | None,
    last_round: LastRoundResult | None,
    results: dict,
) -> tuple[dict[str, float], dict[str, str]]:
    """Heuristic-based default weights with descriptive rationales."""
    weights: dict[str, float] = {}
    rationales: dict[str, str] = {}

    if "comps" in results:
        count = comps.comparable_count if comps else 0
        if count >= 3:
            weights["comps"] = 0.4
            rationales["comps"] = (
                f"Weight 0.40: comparable_count ({count}) >= 3 threshold, strong market signal"
            )
        else:
            weights["comps"] = 0.25
            rationales["comps"] = (
                f"Weight 0.25: comparable_count ({count}) < 3 threshold, limited market data"
            )

    if "dcf" in results:
        n_years = len(dcf.projected_fcfs) if dcf else 0
        dcf_is_estimated = dcf and any("model-estimated" in w for w in dcf.warnings)
        if dcf_is_estimated:
            weights["dcf"] = 0.15
            rationales["dcf"] = (
                f"Weight 0.15: DCF with {n_years}-year projections, model-estimated inputs — significantly reduced weight"
            )
        else:
            weights["dcf"] = 0.35
            rationales["dcf"] = (
                f"Weight 0.35: DCF with {n_years}-year projections, intrinsic value anchor"
            )

    if "last_round" in results:
        months = last_round.months_since_round if last_round else None
        last_round_is_estimated = last_round and any("model-estimated" in w for w in last_round.warnings)
        stale = months is not None and months > 18
        if last_round_is_estimated:
            weights["last_round"] = 0.10
            rationales["last_round"] = (
                f"Weight 0.10: last round data is model-estimated, significantly reduced weight"
            )
        elif stale:
            weights["last_round"] = 0.15
            rationales["last_round"] = (
                f"Weight 0.15: last round {months}mo ago > 18mo staleness threshold, reduced weight"
            )
        else:
            weights["last_round"] = 0.25
            months_str = f"{months}mo ago" if months is not None else "date unknown"
            rationales["last_round"] = (
                f"Weight 0.25: last round {months_str}, within 18mo freshness window"
            )

    return weights, rationales
