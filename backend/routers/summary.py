"""Summary endpoint — returns latest daily snapshot."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.daily_snapshot import DailySnapshot
from backend.schemas.summary import SummaryResponse

router = APIRouter(prefix="", tags=["summary"])


@router.get("/summary", response_model=SummaryResponse)
def get_summary(db: Session = Depends(get_db)) -> SummaryResponse:
    snapshot = (
        db.query(DailySnapshot)
        .order_by(desc(DailySnapshot.snapshot_date))
        .first()
    )

    if not snapshot:
        return SummaryResponse(
            snapshot_date=None,
            total_jobs=0,
            total_companies=0,
            jobs_by_source={},
            jobs_by_seniority={},
            jobs_by_work_type={},
            top_technologies=[],
        )

    return SummaryResponse(
        snapshot_date=snapshot.snapshot_date,
        total_jobs=snapshot.total_jobs,
        total_companies=snapshot.total_companies,
        jobs_by_source=snapshot.jobs_by_source or {},
        jobs_by_seniority=snapshot.jobs_by_seniority or {},
        jobs_by_work_type=snapshot.jobs_by_work_type or {},
        top_technologies=snapshot.top_technologies or [],
    )