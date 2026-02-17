import asyncio
import csv
import io
import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.models.request import ValuationRequest, FinancialProjections
from backend.models.report import ValuationReport
from backend.api.dependencies import get_pipeline, get_db_service
from backend.pipeline.orchestrator import ValuationPipeline
from backend.services.db_service import DBService
from backend.services.pipeline_status import create_status, get_status, cleanup_status

router = APIRouter(prefix="/api/valuations", tags=["valuations"])


def _parse_financial_value(s: str) -> float | None:
    """Parse a financial value like '$ 587,363', '(6,963)', '31.7%'."""
    s = s.strip().replace('$', '').replace(',', '').replace('\xa0', '').strip()
    if not s or s in ('-', '–', 'N/A', '#N/A', '#n/a'):
        return None
    neg = s.startswith('(') and s.endswith(')')
    if neg:
        s = s[1:-1].strip()
    try:
        if s.endswith('%'):
            val = float(s[:-1]) / 100.0
        elif s.rstrip().endswith('x'):
            return None
        else:
            val = float(s)
    except ValueError:
        return None
    return -val if neg else val


def _try_simple_csv(text: str) -> FinancialProjections | None:
    """Try parsing CSV with 'revenue' and 'ebitda_margin' columns."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []
        if 'revenue' not in fieldnames or 'ebitda_margin' not in fieldnames:
            return None
        revenues: list[float] = []
        margins: list[float] = []
        scalar_fields: dict[str, float] = {}
        scalar_keys = {
            "wacc", "tax_rate", "capex_percent",
            "nwc_change_percent", "terminal_growth_rate",
            "depreciation_percent",
        }
        for i, row in enumerate(reader):
            revenues.append(float(row["revenue"]))
            margins.append(float(row["ebitda_margin"]))
            if i == 0:
                for key in scalar_keys:
                    if key in row and row[key].strip():
                        scalar_fields[key] = float(row[key])
        if not revenues:
            return None
        return FinancialProjections(
            revenue_projections=revenues,
            ebitda_margins=margins,
            **scalar_fields,
        )
    except (KeyError, ValueError):
        return None


def _try_dcf_model_csv(text: str) -> FinancialProjections | None:
    """Parse an Excel-exported DCF model CSV."""
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 10:
        return None

    def cell_has(row: list[str], label: str) -> bool:
        return any(label in c.strip().lower() for c in row)

    def extract_projected(row: list[str], start: int, end: int) -> list[float]:
        vals = []
        for j in range(start, min(end + 1, len(row))):
            v = _parse_financial_value(row[j])
            if v is not None:
                vals.append(v)
        return vals

    def find_scalar(label: str) -> float | None:
        for row in rows:
            if cell_has(row, label):
                for cell in row:
                    v = _parse_financial_value(cell)
                    if v is not None:
                        return v
        return None

    # Find projected column range from "Projected:" marker
    proj_start = None
    for row in rows:
        for j, cell in enumerate(row):
            if cell.strip().lower().startswith('projected'):
                proj_start = j
                break
        if proj_start is not None:
            break
    if proj_start is None:
        return None

    # Find last fiscal year column
    proj_end = proj_start
    for row in rows:
        for j, cell in enumerate(row):
            if re.match(r'FY\d{2}', cell.strip()):
                proj_end = max(proj_end, j)
    if proj_end <= proj_start:
        return None

    # Extract projected revenue
    revenues: list[float] = []
    for row in rows:
        if cell_has(row, 'total revenue:'):
            revenues = extract_projected(row, proj_start, proj_end)
            break
    if not revenues:
        for row in rows:
            if cell_has(row, 'net sales:') and not cell_has(row, 'membership'):
                revenues = extract_projected(row, proj_start, proj_end)
                break
    if not revenues:
        return None

    # Extract EBITDA and compute margins
    ebitda_vals: list[float] = []
    for row in rows:
        if (cell_has(row, 'ebitda:')
                and not cell_has(row, 'tev')
                and not cell_has(row, 'margin')
                and not cell_has(row, 'multiple')):
            ebitda_vals = extract_projected(row, proj_start, proj_end)
            break

    margins: list[float] = []
    for i in range(len(revenues)):
        if i < len(ebitda_vals) and revenues[i] > 0:
            margins.append(ebitda_vals[i] / revenues[i])
        else:
            margins.append(0.2)

    # Extract scalar parameters
    kwargs: dict[str, float] = {}

    wacc = find_scalar('discount rate (wacc)')
    if wacc is not None and 0 < wacc < 1:
        kwargs['wacc'] = wacc

    tax = find_scalar('effective tax rate')
    if tax is None:
        tax = find_scalar('tax rate:')
    if tax is not None and 0 < tax < 1:
        kwargs['tax_rate'] = tax

    tgr = find_scalar('baseline terminal fcf growth rate')
    if tgr is None:
        tgr = find_scalar('terminal fcf growth rate')
    if tgr is None:
        tgr = find_scalar('terminal growth rate')
    if tgr is not None and -0.1 <= tgr <= 0.2:
        kwargs['terminal_growth_rate'] = tgr

    # CapEx and D&A percentages from section-context "% Revenue:" rows
    section = None
    for row in rows:
        row_text = ' '.join(c.strip() for c in row)
        if 'Depreciation & Amortization:' in row_text or 'Depreciation:' in row_text:
            section = 'da'
        elif 'Capital Expenditures:' in row_text or 'Capital Expenditure:' in row_text:
            section = 'capex'
        elif '% Revenue:' in row_text or '% revenue:' in row_text:
            vals = extract_projected(row, proj_start, proj_end)
            if vals:
                if section == 'da' and 'depreciation_percent' not in kwargs:
                    kwargs['depreciation_percent'] = abs(vals[0])
                elif section == 'capex' and 'capex_percent' not in kwargs:
                    kwargs['capex_percent'] = abs(vals[0])
            section = None

    # NWC: compute from actual change-in-working-capital values
    for row in rows:
        if cell_has(row, 'change in working capital'):
            wc_vals = extract_projected(row, proj_start, proj_end)
            if wc_vals and revenues:
                ratios = [abs(w) / r for w, r in zip(wc_vals, revenues) if r > 0]
                if ratios:
                    kwargs['nwc_change_percent'] = sum(ratios) / len(ratios)
                    break

    return FinancialProjections(
        revenue_projections=revenues,
        ebitda_margins=margins,
        **kwargs,
    )


def _try_sectioned_csv(text: str) -> FinancialProjections | None:
    """Parse a sectioned CSV with 'Section' column separating Projections and Assumptions."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = [f.strip() for f in (reader.fieldnames or [])]
        if 'Section' not in fieldnames:
            return None

        # Find revenue and margin columns (flexible naming)
        rev_col = next((f for f in fieldnames if 'revenue' in f.lower()), None)
        margin_col = next((f for f in fieldnames if 'ebitda' in f.lower() and 'margin' in f.lower()), None)
        metric_col = next((f for f in fieldnames if f.lower() == 'metric'), None)
        value_col = next((f for f in fieldnames if f.lower() == 'value'), None)

        if not rev_col or not margin_col:
            return None

        # Detect unit multiplier from column header (e.g. "Revenue ($M)" -> 1e6)
        rev_multiplier = 1.0
        rev_lower = rev_col.lower()
        if '($b)' in rev_lower or '(b)' in rev_lower:
            rev_multiplier = 1e9
        elif '($m)' in rev_lower or '(m)' in rev_lower or '($mm)' in rev_lower:
            rev_multiplier = 1e6
        elif '($k)' in rev_lower or '(k)' in rev_lower:
            rev_multiplier = 1e3

        revenues: list[float] = []
        margins: list[float] = []
        assumptions: dict[str, float] = {}

        METRIC_MAP = {
            'wacc': 'wacc',
            'terminal growth': 'terminal_growth_rate',
            'terminal growth rate': 'terminal_growth_rate',
            'tax rate': 'tax_rate',
            'capex % revenue': 'capex_percent',
            'capex percent': 'capex_percent',
            'nwc change % revenue': 'nwc_change_percent',
            'nwc change percent': 'nwc_change_percent',
            'd&a % revenue': 'depreciation_percent',
            'depreciation % revenue': 'depreciation_percent',
            'depreciation percent': 'depreciation_percent',
        }

        for row in reader:
            section = (row.get('Section') or '').strip().lower()
            if section == 'projections':
                rev_str = (row.get(rev_col) or '').strip()
                margin_str = (row.get(margin_col) or '').strip()
                if rev_str:
                    revenues.append(float(rev_str) * rev_multiplier)
                    margins.append(float(margin_str) if margin_str else 0.2)
            elif section == 'assumptions' and metric_col and value_col:
                metric = (row.get(metric_col) or '').strip().lower()
                val_str = (row.get(value_col) or '').strip()
                if metric and val_str:
                    param = METRIC_MAP.get(metric)
                    if param:
                        assumptions[param] = float(val_str)

        if not revenues:
            return None

        return FinancialProjections(
            revenue_projections=revenues,
            ebitda_margins=margins,
            **assumptions,
        )
    except (KeyError, ValueError):
        return None


class ReweightRequest(BaseModel):
    weights: dict[str, float]


@router.post("", response_model=ValuationReport)
async def create_valuation(
    request: ValuationRequest,
    pipeline: ValuationPipeline = Depends(get_pipeline),
):
    """Run full valuation pipeline and return complete report."""
    report = await pipeline.run(request)
    return report


@router.post("/async")
async def create_valuation_async(
    request: ValuationRequest,
    pipeline: ValuationPipeline = Depends(get_pipeline),
):
    """Start pipeline asynchronously, return report_id and stream URL."""
    report_id = str(uuid.uuid4())
    status = create_status(report_id)

    asyncio.create_task(pipeline.run(request, report_id=report_id, status=status))

    return {
        "report_id": report_id,
        "stream_url": f"/api/valuations/{report_id}/stream",
    }


@router.get("/{valuation_id}/stream")
async def stream_pipeline(valuation_id: str):
    """SSE stream of pipeline step events."""
    status = get_status(valuation_id)
    if not status:
        raise HTTPException(status_code=404, detail="No active pipeline for this ID")

    async def event_generator():
        while True:
            events = await status.wait_for_event(timeout=15.0)
            for evt in events:
                data = json.dumps({
                    "type": "step",
                    "step_name": evt.step_name,
                    "status": evt.status,
                    "timestamp": evt.timestamp,
                    "duration_ms": evt.duration_ms,
                    "error": evt.error,
                })
                yield f"data: {data}\n\n"

            if status.complete:
                yield f"data: {json.dumps({'type': 'complete', 'report_id': valuation_id})}\n\n"
                cleanup_status(valuation_id)
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{valuation_id}/reweight", response_model=ValuationReport)
async def reweight_valuation(
    valuation_id: str,
    body: ReweightRequest,
    db: DBService = Depends(get_db_service),
):
    """Adjust methodology weights and recompute blended valuation."""
    report = db.update_weights(valuation_id, body.weights)
    if not report:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return report


@router.get("", response_model=list[dict])
async def list_valuations(db: DBService = Depends(get_db_service)):
    """List all past valuations (summary only)."""
    return db.list_reports()


@router.get("/{valuation_id}", response_model=ValuationReport)
async def get_valuation(
    valuation_id: str,
    db: DBService = Depends(get_db_service),
):
    """Get full valuation report by ID."""
    report = db.get_report(valuation_id)
    if not report:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return report


@router.delete("/{valuation_id}")
async def delete_valuation(
    valuation_id: str,
    db: DBService = Depends(get_db_service),
):
    """Delete a valuation report."""
    deleted = db.delete_report(valuation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Valuation not found")
    return {"status": "deleted"}


@router.get("/{valuation_id}/audit-log")
async def get_audit_log(
    valuation_id: str,
    db: DBService = Depends(get_db_service),
):
    """Get pipeline steps and LLM call logs for a valuation."""
    return db.get_audit_log(valuation_id)


@router.post("/upload-projections", response_model=FinancialProjections)
async def upload_projections(file: UploadFile = File(...)):
    """Parse uploaded JSON or CSV file into FinancialProjections."""
    content = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".json"):
            data = json.loads(content)
            return FinancialProjections(**data)

        elif filename.endswith(".csv"):
            text = content.decode("utf-8")
            result = _try_simple_csv(text)
            if result is None:
                result = _try_sectioned_csv(text)
            if result is None:
                result = _try_dcf_model_csv(text)
            if result is None:
                raise HTTPException(
                    status_code=400,
                    detail="Unrecognized CSV format. Expected either 'revenue'/'ebitda_margin' columns or an Excel DCF model export.",
                )
            return result

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Upload .json or .csv",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")
