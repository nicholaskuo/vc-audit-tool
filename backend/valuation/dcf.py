from backend.models.request import FinancialProjections
from backend.models.valuations import DCFResult, SensitivityCell


def _compute_ev(
    revenue_projections: list[float],
    ebitda_margins: list[float],
    capex_percent: float,
    nwc_change_percent: float,
    tax_rate: float,
    depreciation_percent: float,
    wacc: float,
    tgr: float,
) -> tuple[float, list[float], float]:
    """Core DCF computation. Returns (enterprise_value, fcfs, terminal_value)."""
    n_years = len(revenue_projections)
    fcfs: list[float] = []

    for i in range(n_years):
        revenue = revenue_projections[i]
        margin = ebitda_margins[i] if i < len(ebitda_margins) else ebitda_margins[-1]
        ebitda = revenue * margin
        da = revenue * depreciation_percent
        ebit = ebitda - da
        tax = max(0.0, ebit * tax_rate)
        capex = revenue * capex_percent
        nwc_change = revenue * nwc_change_percent
        fcf = ebitda - tax - capex - nwc_change
        fcfs.append(fcf)

    pv_fcfs = sum(fcf / (1 + wacc) ** (i + 1) for i, fcf in enumerate(fcfs))

    terminal_fcf = fcfs[-1] * (1 + tgr)
    terminal_value = terminal_fcf / (wacc - tgr)
    pv_terminal = terminal_value / (1 + wacc) ** n_years

    enterprise_value = pv_fcfs + pv_terminal
    return enterprise_value, fcfs, terminal_value


def _compute_sensitivity_table(
    revenue_projections: list[float],
    ebitda_margins: list[float],
    capex_percent: float,
    nwc_change_percent: float,
    tax_rate: float,
    depreciation_percent: float,
    base_wacc: float,
    base_tgr: float,
) -> list[SensitivityCell]:
    """Generate 5x5 grid: WACC +/-2% x TGR +/-1%, skip where WACC <= TGR."""
    wacc_steps = [base_wacc + delta for delta in [-0.02, -0.01, 0.0, 0.01, 0.02]]
    tgr_steps = [base_tgr + delta for delta in [-0.01, -0.005, 0.0, 0.005, 0.01]]

    cells: list[SensitivityCell] = []
    for w in wacc_steps:
        for t in tgr_steps:
            if w <= t or w <= 0:
                continue
            ev, _, _ = _compute_ev(
                revenue_projections, ebitda_margins,
                capex_percent, nwc_change_percent, tax_rate,
                depreciation_percent, w, t,
            )
            cells.append(SensitivityCell(
                wacc=round(w, 4),
                terminal_growth_rate=round(t, 4),
                enterprise_value=round(ev, 2),
            ))
    return cells


def compute_dcf_valuation(projections: FinancialProjections) -> DCFResult:
    """Compute enterprise value using discounted cash flow analysis."""
    wacc = projections.wacc
    tgr = projections.terminal_growth_rate
    warnings: list[str] = []

    if wacc <= tgr:
        warnings.append(f"WACC ({wacc}) must be greater than terminal growth rate ({tgr})")
        return DCFResult(
            enterprise_value=0.0,
            projected_fcfs=[],
            terminal_value=0.0,
            discount_rate=wacc,
            terminal_growth_rate=tgr,
            warnings=warnings,
        )

    n_years = len(projections.revenue_projections)
    if n_years == 0:
        warnings.append("No revenue projections provided")
        return DCFResult(
            enterprise_value=0.0,
            projected_fcfs=[],
            terminal_value=0.0,
            discount_rate=wacc,
            terminal_growth_rate=tgr,
            warnings=warnings,
        )

    depreciation_percent = getattr(projections, 'depreciation_percent', 0.0)

    enterprise_value, fcfs, terminal_value = _compute_ev(
        projections.revenue_projections,
        projections.ebitda_margins,
        projections.capex_percent,
        projections.nwc_change_percent,
        projections.tax_rate,
        depreciation_percent,
        wacc,
        tgr,
    )

    sensitivity_table = _compute_sensitivity_table(
        projections.revenue_projections,
        projections.ebitda_margins,
        projections.capex_percent,
        projections.nwc_change_percent,
        projections.tax_rate,
        depreciation_percent,
        wacc,
        tgr,
    )

    return DCFResult(
        enterprise_value=enterprise_value,
        projected_fcfs=fcfs,
        terminal_value=terminal_value,
        discount_rate=wacc,
        terminal_growth_rate=tgr,
        warnings=warnings,
        sensitivity_table=sensitivity_table,
    )
