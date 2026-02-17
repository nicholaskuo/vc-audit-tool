import pytest
from backend.models.request import FinancialProjections
from backend.valuation.dcf import compute_dcf_valuation


def test_basic_dcf():
    proj = FinancialProjections(
        revenue_projections=[100, 120, 140, 160, 180],
        ebitda_margins=[0.20, 0.22, 0.24, 0.26, 0.28],
        wacc=0.12,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    assert result.enterprise_value > 0
    assert len(result.projected_fcfs) == 5
    assert result.terminal_value > 0
    assert not result.warnings


def test_wacc_less_than_tgr():
    proj = FinancialProjections(
        revenue_projections=[100],
        ebitda_margins=[0.20],
        wacc=0.02,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    assert result.enterprise_value == 0.0
    assert any("WACC" in w for w in result.warnings)


def test_wacc_equal_tgr():
    proj = FinancialProjections(
        revenue_projections=[100],
        ebitda_margins=[0.20],
        wacc=0.03,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    assert result.enterprise_value == 0.0


def test_no_projections():
    proj = FinancialProjections(
        revenue_projections=[],
        ebitda_margins=[],
        wacc=0.12,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    assert result.enterprise_value == 0.0
    assert any("No revenue" in w for w in result.warnings)


def test_fcf_calculation():
    """Verify FCF = EBITDA - Tax - CapEx - NWC change (with depreciation_percent=0)."""
    proj = FinancialProjections(
        revenue_projections=[1000],
        ebitda_margins=[0.30],
        capex_percent=0.05,
        nwc_change_percent=0.02,
        tax_rate=0.25,
        wacc=0.10,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    # EBITDA = 300, D&A = 0, EBIT = 300, Tax = 75, CapEx = 50, NWC = 20 → FCF = 155
    assert abs(result.projected_fcfs[0] - 155.0) < 0.01


def test_depreciation_tax_shield():
    """D&A reduces taxable income, increasing FCF vs zero-depreciation case."""
    base = FinancialProjections(
        revenue_projections=[1000],
        ebitda_margins=[0.30],
        capex_percent=0.05,
        nwc_change_percent=0.02,
        tax_rate=0.25,
        wacc=0.10,
        terminal_growth_rate=0.03,
        depreciation_percent=0.0,
    )
    with_da = FinancialProjections(
        revenue_projections=[1000],
        ebitda_margins=[0.30],
        capex_percent=0.05,
        nwc_change_percent=0.02,
        tax_rate=0.25,
        wacc=0.10,
        terminal_growth_rate=0.03,
        depreciation_percent=0.10,
    )
    base_result = compute_dcf_valuation(base)
    da_result = compute_dcf_valuation(with_da)
    # D&A tax shield should increase FCF
    assert da_result.projected_fcfs[0] > base_result.projected_fcfs[0]


def test_depreciation_zero_backward_compatible():
    """depreciation_percent=0 should produce identical results to the old behavior."""
    proj = FinancialProjections(
        revenue_projections=[100, 120, 140],
        ebitda_margins=[0.20, 0.22, 0.24],
        wacc=0.12,
        terminal_growth_rate=0.03,
        depreciation_percent=0.0,
    )
    result = compute_dcf_valuation(proj)
    # Old FCF formula: EBITDA - tax(EBITDA) - CapEx - NWC
    # With depreciation=0: EBIT = EBITDA, tax = max(0, EBIT * 0.25) = EBITDA * 0.25
    rev = 100
    ebitda = 100 * 0.20
    tax = ebitda * 0.25
    capex = 100 * 0.05
    nwc = 100 * 0.02
    expected_fcf = ebitda - tax - capex - nwc
    assert abs(result.projected_fcfs[0] - expected_fcf) < 0.01


def test_sensitivity_table_generated():
    """A basic DCF should produce a sensitivity table."""
    proj = FinancialProjections(
        revenue_projections=[100, 120, 140],
        ebitda_margins=[0.20, 0.22, 0.24],
        wacc=0.12,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    assert len(result.sensitivity_table) > 0
    # Base case should be in the table
    base_cell = next(
        (c for c in result.sensitivity_table
         if abs(c.wacc - 0.12) < 0.001 and abs(c.terminal_growth_rate - 0.03) < 0.001),
        None,
    )
    assert base_cell is not None


def test_sensitivity_base_case_matches():
    """The sensitivity table's base case cell should match the main EV."""
    proj = FinancialProjections(
        revenue_projections=[100, 120, 140],
        ebitda_margins=[0.20, 0.22, 0.24],
        wacc=0.12,
        terminal_growth_rate=0.03,
    )
    result = compute_dcf_valuation(proj)
    base_cell = next(
        c for c in result.sensitivity_table
        if abs(c.wacc - 0.12) < 0.001 and abs(c.terminal_growth_rate - 0.03) < 0.001
    )
    assert abs(base_cell.enterprise_value - result.enterprise_value) < 1.0
