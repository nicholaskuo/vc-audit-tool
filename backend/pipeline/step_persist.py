from backend.models.report import ValuationReport
from backend.services.db_service import DBService


def persist_report(report: ValuationReport, db: DBService) -> str:
    """Step 6: Save the completed report to SQLite."""
    return db.save_report(report)
