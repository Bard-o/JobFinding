"""Company model."""

from sqlalchemy import Column, DateTime, Integer, String

from backend.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, server_default="NOW()")