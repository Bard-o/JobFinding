"""Source model."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    base_url = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default="NOW()")