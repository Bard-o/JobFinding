"""Pydantic schemas for job-related endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    country: Optional[str] = None
    published_at: Optional[date] = None
    url: str
    work_type: Optional[str] = None
    seniority: Optional[str] = None


class JobDetailResponse(JobResponse):
    description: Optional[str] = None
    salary_raw: Optional[str] = None
    scraped_at: datetime
    technologies: list[str] = []


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedJobResponse(BaseModel):
    """Paginated response with metadata."""

    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int