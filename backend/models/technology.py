"""Technology model."""

from sqlalchemy import Column, DateTime, Integer, String

from backend.database import Base


class Technology(Base):
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default="NOW()")