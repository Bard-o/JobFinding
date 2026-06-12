"""Genera snapshots diarios de métricas del sistema.

Calcula agregaciones de jobs, companies, technologies y las guarda
en daily_snapshots. Se ejecuta al final de cada ejecución del scraper
(después de ETL y quality checks).

Usa ON CONFLICT (snapshot_date) DO UPDATE para ser idempotente — si ya
existe un snapshot para hoy, lo actualiza con los datos más recientes.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = structlog.get_logger(__name__)

# Top N tecnologías a incluir en el snapshot
TOP_TECHNOLOGIES_COUNT = 20


def generate(engine: Engine | None = None) -> dict[str, Any]:
    """Genera un snapshot diario de todas las métricas.

    Calcula agregaciones desde la DB y hace upsert en daily_snapshots.
    Si engine es None, crea uno desde DATABASE_URL.

    Args:
        engine: SQLAlchemy engine. Si es None, usa Settings.from_env().

    Returns:
        Dict con snapshot_date, metrics y counts.
    """
    if engine is None:
        from sqlalchemy import create_engine

        from scraper.config import Settings

        settings = Settings.from_env()
        engine = create_engine(settings.database_url)

    today = date.today()

    with engine.begin() as conn:
        # ── Calcular métricas ──────────────────────────────────────────

        # total_jobs
        total_jobs = _get_total_jobs(conn)

        # total_companies
        total_companies = _get_total_companies(conn)

        # jobs_by_source
        jobs_by_source = _get_jobs_by_source(conn)

        # jobs_by_seniority
        jobs_by_seniority = _get_jobs_by_seniority(conn)

        # jobs_by_work_type
        jobs_by_work_type = _get_jobs_by_work_type(conn)

        # top_technologies (top 20)
        top_technologies = _get_top_technologies(conn, TOP_TECHNOLOGIES_COUNT)

        # ── Upsert en daily_snapshots ───────────────────────────────────

        conn.execute(
            text(
                """
                INSERT INTO daily_snapshots
                    (snapshot_date, total_jobs, total_companies,
                     jobs_by_source, jobs_by_seniority, jobs_by_work_type,
                     top_technologies)
                VALUES
                    (:snapshot_date, :total_jobs, :total_companies,
                     :jobs_by_source, :jobs_by_seniority, :jobs_by_work_type,
                     :top_technologies)
                ON CONFLICT (snapshot_date) DO UPDATE SET
                    total_jobs = EXCLUDED.total_jobs,
                    total_companies = EXCLUDED.total_companies,
                    jobs_by_source = EXCLUDED.jobs_by_source,
                    jobs_by_seniority = EXCLUDED.jobs_by_seniority,
                    jobs_by_work_type = EXCLUDED.jobs_by_work_type,
                    top_technologies = EXCLUDED.top_technologies,
                    created_at = CURRENT_TIMESTAMP
            """
            ),
            {
                "snapshot_date": today,
                "total_jobs": total_jobs,
                "total_companies": total_companies,
                "jobs_by_source": json.dumps(jobs_by_source),
                "jobs_by_seniority": json.dumps(jobs_by_seniority),
                "jobs_by_work_type": json.dumps(jobs_by_work_type),
                "top_technologies": json.dumps(top_technologies),
            },
        )

    logger.info(
        "snapshot_generated",
        snapshot_date=today.isoformat(),
        total_jobs=total_jobs,
        total_companies=total_companies,
        top_tech_count=len(top_technologies),
    )

    return {
        "snapshot_date": today.isoformat(),
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "jobs_by_source": jobs_by_source,
        "jobs_by_seniority": jobs_by_seniority,
        "jobs_by_work_type": jobs_by_work_type,
        "top_technologies": top_technologies,
    }


def _get_total_jobs(conn) -> int:
    result = conn.execute(text("SELECT COUNT(*) FROM jobs"))
    return result.scalar() or 0


def _get_total_companies(conn) -> int:
    result = conn.execute(text("SELECT COUNT(*) FROM companies"))
    return result.scalar() or 0


def _get_jobs_by_source(conn) -> dict[str, int]:
    result = conn.execute(
        text(
            """
        SELECT s.name, COUNT(j.id)
        FROM sources s
        LEFT JOIN jobs j ON j.source_id = s.id
        GROUP BY s.name
    """
        )
    )
    return {row[0]: row[1] for row in result}


def _get_jobs_by_seniority(conn) -> dict[str, int]:
    result = conn.execute(
        text(
            """
        SELECT COALESCE(seniority, 'unknown'), COUNT(*)
        FROM jobs
        GROUP BY COALESCE(seniority, 'unknown')
    """
        )
    )
    return {row[0]: row[1] for row in result}


def _get_jobs_by_work_type(conn) -> dict[str, int]:
    result = conn.execute(
        text(
            """
        SELECT COALESCE(work_type, 'unknown'), COUNT(*)
        FROM jobs
        GROUP BY COALESCE(work_type, 'unknown')
    """
        )
    )
    return {row[0]: row[1] for row in result}


def _get_top_technologies(conn, limit: int) -> list[dict[str, Any]]:
    result = conn.execute(
        text(
            """
        SELECT t.name, t.category, COUNT(jt.job_id) as job_count
        FROM technologies t
        JOIN job_technologies jt ON jt.technology_id = t.id
        GROUP BY t.name, t.category
        ORDER BY job_count DESC
        LIMIT :limit
    """
        ),
        {"limit": limit},
    )

    return [
        {"name": row[0], "category": row[1], "count": row[2]}
        for row in result
    ]