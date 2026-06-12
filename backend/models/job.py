"""Job model."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"))
    title = Column(String(255), nullable=False)
    country = Column(String(100))
    published_at = Column(Date)
    url = Column(Text, unique=True, nullable=False)
    work_type = Column(String(20))
    description = Column(Text)
    salary_raw = Column(Text)
    seniority = Column(String(20))
    scraped_at = Column(DateTime, server_default="NOW()")
    created_at = Column(DateTime, server_default="NOW()")

    source = relationship("Source")
    company = relationship("Company")
    technologies = relationship("Technology", secondary="job_technologies")