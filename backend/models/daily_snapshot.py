"""DailySnapshot model."""

from sqlalchemy import Column, Date, DateTime, Integer, JSON

from backend.database import Base


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(Date, unique=True, nullable=False)
    total_jobs = Column(Integer, nullable=False)
    total_companies = Column(Integer, nullable=False)
    jobs_by_source = Column(JSON)
    jobs_by_seniority = Column(JSON)
    jobs_by_work_type = Column(JSON)
    top_technologies = Column(JSON)
    created_at = Column(DateTime, server_default="NOW()")