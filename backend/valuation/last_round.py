from datetime import datetime, timezone
from backend.models.market_data import IndexData
from backend.models.valuations import LastRoundResult


def compute_last_round_valuation(
    last_valuation: float,
    last_round_date: str,
    index_data: IndexData | None,
) -> LastRoundResult:
    """Adjust last-round valuation by market index performance."""
    warnings: list[str] = []

    # Calculate months since round
    try:
        round_date = datetime.strptime(last_round_date, "%Y-%m-%d")
        months_since = (datetime.now(timezone.utc).replace(tzinfo=None) - round_date).days // 30
    except (ValueError, TypeError):
        months_since = None
        warnings.append(f"Could not parse round date: {last_round_date}")

    if months_since is not None and months_since > 18:
        warnings.append(f"Last round was {months_since} months ago — valuation may be stale")

    # Apply index adjustment
    index_return = None
    adjustment_factor = 1.0

    if index_data and index_data.return_since_round is not None:
        index_return = index_data.return_since_round
        adjustment_factor = 1.0 + index_return
    else:
        warnings.append("No index data available — using unadjusted last-round valuation")

    enterprise_value = last_valuation * adjustment_factor

    return LastRoundResult(
        enterprise_value=enterprise_value,
        last_round_valuation=last_valuation,
        index_return=index_return,
        adjustment_factor=adjustment_factor,
        months_since_round=months_since,
        warnings=warnings,
    )
