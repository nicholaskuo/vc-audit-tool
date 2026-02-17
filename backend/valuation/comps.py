import math
import statistics
from backend.models.market_data import CompanyFinancials
from backend.models.valuations import CompsResult, CompSelectionScore

# Sector groupings for cross-sector relevance scoring
_TECH_SECTORS = {"Technology", "Information Technology", "Software", "SaaS"}
_CONSUMER_SECTORS = {"Consumer Cyclical", "Consumer Defensive", "Retail"}
_HEALTH_SECTORS = {"Healthcare", "Biotechnology", "Pharmaceuticals"}
_FINANCE_SECTORS = {"Financial Services", "Fintech", "Insurance"}

_SECTOR_GROUPS = [_TECH_SECTORS, _CONSUMER_SECTORS, _HEALTH_SECTORS, _FINANCE_SECTORS]


def _sectors_related(sector_a: str | None, sector_b: str | None) -> float:
    """Return sector relatedness: 1.0 exact match, 0.5 same group, 0.0 different."""
    if not sector_a or not sector_b:
        return 0.5  # unknown → give benefit of the doubt
    if sector_a.lower() == sector_b.lower():
        return 1.0
    for group in _SECTOR_GROUPS:
        lower_group = {s.lower() for s in group}
        if sector_a.lower() in lower_group and sector_b.lower() in lower_group:
            return 0.5
    return 0.0


def _size_proximity_score(comp_revenue: float | None, target_revenue: float) -> float:
    """Score 0-1 based on log-ratio of revenues. Exclude outside 0.1x-10x range."""
    if not comp_revenue or comp_revenue <= 0 or target_revenue <= 0:
        return 0.0
    ratio = comp_revenue / target_revenue
    if ratio < 0.1 or ratio > 10.0:
        return 0.0
    log_ratio = abs(math.log10(ratio))
    return max(0.0, 1.0 - log_ratio)


def _data_quality_score(comp: CompanyFinancials) -> float:
    """Score 0-1 based on proportion of non-null key fields. Must have ev_to_revenue."""
    if comp.ev_to_revenue is None or comp.ev_to_revenue <= 0:
        return 0.0
    fields = [comp.market_cap, comp.enterprise_value, comp.revenue, comp.ebitda,
              comp.ev_to_revenue, comp.ev_to_ebitda]
    filled = sum(1 for f in fields if f is not None)
    return filled / len(fields)


def score_and_filter_comps(
    comparables: list[CompanyFinancials],
    target_revenue: float,
    target_sector: str | None = None,
    sector_weight: float = 0.3,
    size_weight: float = 0.4,
    quality_weight: float = 0.3,
    min_composite: float = 0.3,
) -> tuple[list[CompanyFinancials], list[CompSelectionScore]]:
    """Score all comparables and filter to those meeting threshold.

    Returns (included_comps, all_scores_including_excluded).
    """
    scores: list[CompSelectionScore] = []
    included: list[CompanyFinancials] = []

    for comp in comparables:
        s_score = _sectors_related(target_sector, comp.sector)
        sz_score = _size_proximity_score(comp.revenue, target_revenue) if target_revenue > 0 else 0.5
        dq_score = _data_quality_score(comp)

        composite = (s_score * sector_weight + sz_score * size_weight + dq_score * quality_weight)

        exclusion_reason = None
        is_included = True

        if dq_score == 0.0:
            is_included = False
            exclusion_reason = "Missing EV/Revenue data"
        elif sz_score == 0.0 and target_revenue > 0:
            is_included = False
            exclusion_reason = "Revenue outside 0.1x-10x range of target"
        elif composite < min_composite:
            is_included = False
            exclusion_reason = f"Composite score {composite:.2f} below {min_composite} threshold"

        if is_included:
            included.append(comp)

        scores.append(CompSelectionScore(
            ticker=comp.ticker,
            name=comp.name,
            included=is_included,
            sector_score=round(s_score, 2),
            size_proximity_score=round(sz_score, 2),
            data_quality_score=round(dq_score, 2),
            composite_score=round(composite, 2),
            exclusion_reason=exclusion_reason,
        ))

    return included, scores


def compute_comps_valuation(
    target_revenue: float,
    target_ebitda: float | None,
    comparables: list[CompanyFinancials],
    target_sector: str | None = None,
) -> CompsResult:
    """Compute enterprise value using comparable company multiples."""
    warnings: list[str] = []

    # Score and filter comps if sector is available
    if target_sector is not None:
        filtered, selection_scores = score_and_filter_comps(
            comparables, target_revenue, target_sector
        )
        selection_criteria = {
            "sector_weight": 0.3,
            "size_weight": 0.4,
            "quality_weight": 0.3,
            "min_composite": 0.3,
            "target_sector": target_sector,
            "target_revenue": target_revenue,
        }
    else:
        # No sector info — use all comps with valid ev_to_revenue (legacy behavior)
        filtered = comparables
        selection_scores = []
        selection_criteria = {}

    valid = [c for c in filtered if c.ev_to_revenue is not None and c.ev_to_revenue > 0]

    if len(valid) < 2:
        warnings.append(f"Only {len(valid)} valid comparable(s) with EV/Revenue data")

    if not valid:
        return CompsResult(
            enterprise_value=0.0,
            ev_to_revenue_median=0.0,
            ev_to_revenue_mean=0.0,
            comparable_count=0,
            comparables_used=[],
            warnings=warnings + ["No valid comparables available"],
            comp_selection_scores=selection_scores,
            selection_criteria=selection_criteria,
        )

    ev_rev_values = [c.ev_to_revenue for c in valid]
    ev_rev_median = statistics.median(ev_rev_values)
    ev_rev_mean = statistics.mean(ev_rev_values)

    # Use median multiple for primary valuation
    enterprise_value = target_revenue * ev_rev_median

    # EBITDA multiples (optional)
    ebitda_valid = [c for c in filtered if c.ev_to_ebitda is not None and c.ev_to_ebitda > 0]
    ev_ebitda_median = None
    ev_ebitda_mean = None
    if ebitda_valid:
        ebitda_values = [c.ev_to_ebitda for c in ebitda_valid]
        ev_ebitda_median = statistics.median(ebitda_values)
        ev_ebitda_mean = statistics.mean(ebitda_values)

    return CompsResult(
        enterprise_value=enterprise_value,
        ev_to_revenue_median=ev_rev_median,
        ev_to_revenue_mean=ev_rev_mean,
        ev_to_ebitda_median=ev_ebitda_median,
        ev_to_ebitda_mean=ev_ebitda_mean,
        comparable_count=len(valid),
        comparables_used=[c.ticker for c in valid],
        warnings=warnings,
        comp_selection_scores=selection_scores,
        selection_criteria=selection_criteria,
    )
