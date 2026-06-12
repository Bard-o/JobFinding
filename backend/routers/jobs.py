"""Jobs endpoints with pagination and filters."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.company import Company
from backend.models.job import Job
from backend.models.job_technology import JobTechnology
from backend.models.technology import Technology
from backend.schemas.job import JobDetailResponse, JobResponse, PaginatedJobResponse

router = APIRouter(prefix="", tags=["jobs"])


@router.get("/jobs", response_model=PaginatedJobResponse)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tech: Optional[str] = None,
    seniority: Optional[str] = None,
    work_type: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db),
) -> PaginatedJobResponse:
    """Listado paginado de jobs con filtros opcionales."""
    query = db.query(Job)

    # Apply filters
    filters = []
    if tech:
        query = query.join(Job.technologies).filter(
            func.lower(Technology.name) == tech.lower()
        )
    if seniority:
        filters.append(Job.seniority == seniority)
    if work_type:
        filters.append(Job.work_type == work_type)
    if country:
        filters.append(Job.country.ilike(f"%{country}%"))

    if filters:
        query = query.filter(and_(*filters))

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    items = []
    for j in jobs:
        items.append(
            JobResponse(
                id=j.id,
                title=j.title,
                company=j.company.name if j.company else "",
                country=j.country,
                published_at=j.published_at,
                url=j.url,
                work_type=j.work_type,
                seniority=j.seniority,
            )
        )

    return PaginatedJobResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetailResponse:
    """Detalle de una oferta."""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tech_names = [t.name for t in job.technologies]

    return JobDetailResponse(
        id=job.id,
        title=job.title,
        company=job.company.name if job.company else "",
        country=job.country,
        published_at=job.published_at,
        url=job.url,
        work_type=job.work_type,
        seniority=job.seniority,
        description=job.description,
        salary_raw=job.salary_raw,
        scraped_at=job.scraped_at,
        technologies=tech_names,
    )