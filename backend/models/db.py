from sqlalchemy import Column, String, Text, DateTime, Float, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class ValuationRecord(Base):
    __tablename__ = "valuation_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String, nullable=False)
    fair_value = Column(Float, nullable=True)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    valuation_id = Column(String, nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    duration_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LLMCallRecord(Base):
    __tablename__ = "llm_call_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    valuation_id = Column(String, nullable=False)
    step_name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
