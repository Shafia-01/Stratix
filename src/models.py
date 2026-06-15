"""
SQLAlchemy ORM models for Keylytics database tables.

Tables:
  keywords          — keyword findings from research runs
  intent_cache      — cached intent classification results
  monitoring_jobs   — APScheduler-backed keyword monitoring job configs
  research_run_logs — audit log of every automated research run
  report_diffs      — serialised ReportDiff between consecutive runs
  eval_results      — LLM-as-judge evaluation scores per run
"""

from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    Text,
)

Base = declarative_base()


class Keyword(Base):
    """Core keyword finding record."""
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seed = Column(String(255), nullable=True)
    keyword = Column(String(255), nullable=False, unique=True, index=True)
    volume = Column(Float, nullable=True)
    competition = Column(Float, nullable=True)
    cpc = Column(Float, nullable=True)
    trend = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    difficulty = Column(String(50), nullable=True)
    intent = Column(String(50), nullable=True)
    competitors = Column(Text, nullable=True)  # JSON string
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntentCache(Base):
    """Cached intent classification results to avoid redundant LLM calls."""
    __tablename__ = "intent_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, unique=True, index=True)
    intent = Column(String(50), nullable=False)


class MonitoringJobModel(Base):
    """Persisted configuration for recurring keyword monitoring jobs."""
    __tablename__ = "monitoring_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), nullable=False, unique=True, index=True)
    seed_keyword = Column(String(255), nullable=False, index=True)
    interval_hours = Column(Integer, nullable=False, default=24)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="active")  # active | paused | failed
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchRunLog(Base):
    """Audit log of every research run, both manual and scheduled."""
    __tablename__ = "research_run_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(255), nullable=False, unique=True, index=True)
    seed_keyword = Column(String(255), nullable=False, index=True)
    triggered_by = Column(String(50), nullable=False, default="manual")  # manual | scheduler
    status = Column(String(50), nullable=False, default="pending")
    strategy_report = Column(Text, nullable=True)   # JSON string of StrategyReport dict
    confidence_scores = Column(Text, nullable=True)  # JSON string
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ReportDiffModel(Base):
    """Serialised diff between two consecutive StrategyReport runs for a keyword."""
    __tablename__ = "report_diffs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_keyword = Column(String(255), nullable=False, index=True)
    prev_run_id = Column(String(255), nullable=True)
    curr_run_id = Column(String(255), nullable=True)
    diff_json = Column(Text, nullable=False)   # JSON serialisation of ReportDiff
    generated_at = Column(DateTime, default=datetime.utcnow)


class EvalResultModel(Base):
    """LLM-as-judge evaluation result for a single research run aspect."""
    __tablename__ = "eval_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(255), nullable=False, index=True)
    eval_type = Column(String(50), nullable=False)   # plan_quality | report_quality | tool_reliability
    score = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    dimension_scores = Column(Text, nullable=True)   # JSON string
    evaluated_at = Column(DateTime, default=datetime.utcnow)
