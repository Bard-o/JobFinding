"""JobTechnology association model."""

from sqlalchemy import Column, ForeignKey, Integer

from backend.database import Base


class JobTechnology(Base):
    __tablename__ = "job_technologies"

    job_id = Column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    technology_id = Column(
        Integer, ForeignKey("technologies.id"), primary_key=True
    )