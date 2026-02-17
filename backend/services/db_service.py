import json
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from backend.models.db import Base, ValuationRecord, AuditLogEntry, LLMCallRecord
from backend.models.report import ValuationReport, PipelineStep, LLMCallLog
from backend.models.valuations import BlendedValuation

logger = logging.getLogger(__name__)


class DBService:
    def __init__(self, database_url: str | None = None):
        url = database_url or os.getenv("DATABASE_URL", "sqlite:///./valuation.db")
        self.engine = create_engine(url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_report(self, report: ValuationReport) -> str:
        session = self.Session()
        try:
            fair_value = None
            if report.blended_valuation:
                fv = report.blended_valuation.get("fair_value")
                if fv is not None:
                    fair_value = float(fv)

            record = ValuationRecord(
                id=report.id,
                company_name=report.company_name,
                fair_value=fair_value,
                report_json=report.model_dump_json(),
                created_at=report.created_at,
            )
            session.merge(record)

            # Save audit log entries
            for step in report.pipeline_steps:
                entry = AuditLogEntry(
                    valuation_id=report.id,
                    step_name=step.step_name,
                    status=step.status,
                    duration_ms=step.duration_ms,
                    error=step.error,
                )
                session.add(entry)

            # Save LLM call records
            for log in report.llm_call_logs:
                rec = LLMCallRecord(
                    valuation_id=report.id,
                    step_name=log.step_name,
                    model=log.model,
                    system_prompt=log.system_prompt,
                    user_prompt=log.user_prompt,
                    response=log.response,
                    tokens_used=log.tokens_used,
                    duration_ms=log.duration_ms,
                )
                session.add(rec)

            session.commit()
            return report.id
        finally:
            session.close()

    def get_report(self, report_id: str) -> ValuationReport | None:
        session = self.Session()
        try:
            record = session.query(ValuationRecord).filter_by(id=report_id).first()
            if not record:
                return None
            return ValuationReport.model_validate_json(record.report_json)
        finally:
            session.close()

    def list_reports(self) -> list[dict]:
        session = self.Session()
        try:
            records = session.query(ValuationRecord).order_by(desc(ValuationRecord.created_at)).all()
            return [
                {
                    "id": r.id,
                    "company_name": r.company_name,
                    "fair_value": r.fair_value,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            session.close()

    def delete_report(self, report_id: str) -> bool:
        session = self.Session()
        try:
            record = session.query(ValuationRecord).filter_by(id=report_id).first()
            if not record:
                return False
            session.query(AuditLogEntry).filter_by(valuation_id=report_id).delete()
            session.query(LLMCallRecord).filter_by(valuation_id=report_id).delete()
            session.delete(record)
            session.commit()
            return True
        finally:
            session.close()

    def update_weights(self, report_id: str, custom_weights: dict[str, float]) -> ValuationReport | None:
        """Re-run only the blender with new weights (pure function, no full pipeline)."""
        from backend.valuation.blender import compute_blended_valuation
        from backend.models.valuations import CompsResult, DCFResult, LastRoundResult

        report = self.get_report(report_id)
        if not report or not report.blended_valuation:
            return None

        bv = report.blended_valuation
        comps = CompsResult(**bv["comps_result"]) if bv.get("comps_result") else None
        dcf = DCFResult(**bv["dcf_result"]) if bv.get("dcf_result") else None
        last_round = LastRoundResult(**bv["last_round_result"]) if bv.get("last_round_result") else None

        new_blended = compute_blended_valuation(comps, dcf, last_round, custom_weights)
        report.blended_valuation = new_blended.model_dump()

        # Persist updated report
        session = self.Session()
        try:
            record = session.query(ValuationRecord).filter_by(id=report_id).first()
            if record:
                record.report_json = report.model_dump_json()
                record.fair_value = new_blended.fair_value
                session.commit()
        finally:
            session.close()

        return report

    def get_audit_log(self, report_id: str) -> dict:
        session = self.Session()
        try:
            steps = session.query(AuditLogEntry).filter_by(valuation_id=report_id).all()
            llm_calls = session.query(LLMCallRecord).filter_by(valuation_id=report_id).all()
            return {
                "pipeline_steps": [
                    {
                        "step_name": s.step_name,
                        "status": s.status,
                        "duration_ms": s.duration_ms,
                        "error": s.error,
                    }
                    for s in steps
                ],
                "llm_calls": [
                    {
                        "step_name": c.step_name,
                        "model": c.model,
                        "system_prompt": c.system_prompt,
                        "user_prompt": c.user_prompt,
                        "response": c.response,
                        "tokens_used": c.tokens_used,
                        "duration_ms": c.duration_ms,
                    }
                    for c in llm_calls
                ],
            }
        finally:
            session.close()
