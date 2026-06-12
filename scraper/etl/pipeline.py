"""ETL pipeline — normalize, validate, and upsert job data into PostgreSQL.

Orchestrates company upsert, job batch insert, and technology tag linking
using SQLAlchemy Core for high-performance batch operations.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine

from scraper.alerts.telegram import send_alert
from scraper.models import JobData

logger = structlog.get_logger(__name__)

# Batch size for database inserts
BATCH_SIZE = 100

# Required fields for data quality validation
REQUIRED_FIELDS = ("title", "company", "url", "published_at")


def run_etl(jobs: List[JobData], engine: Engine, source_id: int = 1) -> dict:
    """Extract, transform, and load job data into PostgreSQL.

    Performs data quality validation, company upsert, job batch insert
    (ON CONFLICT url DO NOTHING), and technology tag resolution/linking.
    Processes jobs in batches of 100 for performance.

    Args:
        jobs: List of extracted JobData objects to upsert.
        engine: SQLAlchemy engine connected to the target database.
        source_id: Source identifier (default: 1 = GetOnBoard).

    Returns:
        A dict with counts: inserted_jobs, existing_jobs, skipped_invalid,
        companies_upserted, tech_links_created.
    """
    stats = {
        "inserted_jobs": 0,
        "existing_jobs": 0,
        "skipped_invalid": 0,
        "companies_upserted": 0,
        "tech_links_created": 0,
    }

    # Step 1: Validate jobs — reject those missing required fields
    valid_jobs: List[JobData] = []
    for job in jobs:
        if not _is_valid_job(job):
            stats["skipped_invalid"] += 1
            logger.warning(
                "job_skipped_invalid",
                url=job.url,
                title=job.title,
                company=job.company,
                published_at=str(job.published_at),
            )
            continue
        valid_jobs.append(job)

    if not valid_jobs:
        logger.warning("etl_no_valid_jobs", total_received=len(jobs))
        send_alert(
            f"⚠️ GetOnBoard scraper: all {len(jobs)} jobs were invalid "
            f"and skipped. Check extraction logic."
        )
        return stats

    logger.info("etl_validation_done", total=len(jobs), valid=len(valid_jobs), invalid=stats["skipped_invalid"])

    # Step 2: Upsert companies and collect name→id mapping
    company_ids = _upsert_companies(valid_jobs, engine)
    stats["companies_upserted"] = len(company_ids)

    # Step 3: Batch insert jobs with ON CONFLICT (url) DO NOTHING
    (
        stats["inserted_jobs"],
        stats["existing_jobs"],
    ) = _insert_jobs(valid_jobs, company_ids, engine, source_id)

    # Step 4: Link technology tags
    stats["tech_links_created"] = _link_technologies(valid_jobs, engine)

    logger.info("etl_complete", **stats)

    if stats["inserted_jobs"] == 0 and len(valid_jobs) > 0:
        send_alert(
            f"⚠️ GetOnBoard scraper: 0 new jobs inserted out of "
            f"{len(valid_jobs)} valid jobs. All may already exist in DB."
        )

    return stats


def _is_valid_job(job: JobData) -> bool:
    """Check that a job has all required fields populated.

    Required fields: title, company, url, published_at.
    A field is invalid if it is None, empty string, or (for strings)
    whitespace-only.
    """
    if not job.url or not job.url.strip():
        return False
    if not job.title or not job.title.strip():
        return False
    if not job.company or not job.company.strip():
        return False
    if job.published_at is None:
        return False
    return True


def _upsert_companies(
    jobs: List[JobData], engine: Engine
) -> dict[str, int]:
    """Upsert unique company names and return a name→id mapping.

    Uses INSERT ... ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
    RETURNING id to get existing IDs without a separate SELECT.
    """
    unique_companies = sorted({job.company for job in jobs})
    company_ids: dict[str, int] = {}

    with engine.begin() as conn:
        for company_name in unique_companies:
            result = conn.execute(
                text(
                    "INSERT INTO companies (name) VALUES (:name) "
                    "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING id"
                ),
                {"name": company_name},
            )
            row = result.fetchone()
            if row is not None:
                company_ids[company_name] = row[0]

    logger.debug("companies_upserted", count=len(company_ids))
    return company_ids


def _insert_jobs(
    jobs: List[JobData],
    company_ids: dict[str, int],
    engine: Engine,
    source_id: int,
) -> tuple[int, int]:
    """Batch insert jobs using INSERT ... ON CONFLICT (url) DO NOTHING.

    Processes jobs in batches of BATCH_SIZE for performance.
    Returns (inserted_count, existing_count).
    """
    inserted = 0
    existing = 0

    with engine.begin() as conn:
        for i in range(0, len(jobs), BATCH_SIZE):
            batch = jobs[i : i + BATCH_SIZE]
            for job in batch:
                company_id = company_ids.get(job.company)
                result = conn.execute(
                    text(
                        "INSERT INTO jobs "
                        "(source_id, company_id, title, country, published_at, "
                        "url, work_type, description, salary_raw, seniority) "
                        "VALUES (:source_id, :company_id, :title, :country, "
                        ":published_at, :url, :work_type, :description, "
                        ":salary_raw, :seniority) "
                        "ON CONFLICT (url) DO NOTHING"
                    ),
                    {
                        "source_id": source_id,
                        "company_id": company_id,
                        "title": job.title,
                        "country": job.country,
                        "published_at": job.published_at,
                        "url": job.url,
                        "work_type": job.work_type,
                        "description": job.description,
                        "salary_raw": job.salary_raw,
                        "seniority": job.seniority,
                    },
                )
                rowcount = result.rowcount
                if rowcount == 0:
                    existing += 1
                else:
                    inserted += 1

            logger.debug(
                "jobs_batch_inserted",
                batch_start=i,
                batch_end=min(i + BATCH_SIZE, len(jobs)),
            )

    return inserted, existing


def _link_technologies(jobs: List[JobData], engine: Engine) -> int:
    """Resolve technology tags and link them to jobs.

    For each job's tags, looks up technology IDs by name (case-insensitive)
    and inserts job_technology associations. Unknown tags are silently skipped.
    """
    total_links = 0

    with engine.begin() as conn:
        # Cache technology lookups to avoid repeated queries
        tech_cache: dict[str, Optional[int]] = {}

        for job in jobs:
            if not job.tags:
                continue

            # Look up the job ID by URL
            job_result = conn.execute(
                text("SELECT id FROM jobs WHERE url = :url"),
                {"url": job.url},
            )
            job_row = job_result.fetchone()
            if job_row is None:
                # Job may have been skipped by ON CONFLICT DO NOTHING
                continue
            job_id = job_row[0]

            for tag in job.tags:
                tag_lower = tag.lower().strip()

                # Check cache first
                if tag_lower in tech_cache:
                    tech_id = tech_cache[tag_lower]
                else:
                    # Look up technology by name (case-insensitive)
                    tech_result = conn.execute(
                        text(
                            "SELECT id FROM technologies "
                            "WHERE LOWER(name) = LOWER(:tag)"
                        ),
                        {"tag": tag},
                    )
                    tech_row = tech_result.fetchone()
                    if tech_row is None:
                        tech_cache[tag_lower] = None
                        logger.debug("tech_tag_unknown", tag=tag)
                        continue
                    tech_id = tech_row[0]
                    tech_cache[tag_lower] = tech_id

                if tech_id is None:
                    continue

                # Link job to technology (skip if already exists)
                conn.execute(
                    text(
                        "INSERT INTO job_technologies (job_id, technology_id) "
                        "VALUES (:job_id, :tech_id) "
                        "ON CONFLICT (job_id, technology_id) DO NOTHING"
                    ),
                    {"job_id": job_id, "tech_id": tech_id},
                )
                total_links += 1

    logger.debug("tech_links_created", count=total_links)
    return total_links


def run_pipeline(engine: Engine) -> dict:
    """Procesa jobs existentes sin tecnología linkada.

    Para cada job en la DB que no tiene tecnologías linkeadas:
    1. Extrae tecnologías desde la descripción (usando tech_extractor)
    2. Extrae seniority desde la descripción (usando seniority_extractor)
    3. Actualiza job_technologies y jobs.seniority

    Args:
        engine: SQLAlchemy engine connected to the target database.

    Returns:
        Dict con counts de jobs procesados, tecnologías linkeadas, etc.
    """
    from scraper.extractors import seniority_extractor, tech_extractor

    # Cargar diccionario de tecnologías
    tech_extractor.load_technology_dict(engine)

    stats = {
        "jobs_processed": 0,
        "tech_links_created": 0,
        "seniority_updated": 0,
    }

    # Buscar jobs sin tecnología linkada (o con seniority NULL)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT j.id, j.description, j.seniority "
                "FROM jobs j "
                "LEFT JOIN job_technologies jt ON j.id = jt.job_id "
                "WHERE jt.job_id IS NULL OR j.seniority IS NULL"
            )
        )
        rows = result.fetchall()

    for row in rows:
        job_id = row[0]
        description = row[1]
        current_seniority = row[2]

        # Extraer y linkear tecnologías
        links = tech_extractor.link_technologies_from_description(
            job_id, description, engine
        )
        if links > 0:
            stats["tech_links_created"] += links

        # Extraer y actualizar seniority
        new_seniority = seniority_extractor.extract_seniority_from_text(description)
        if new_seniority and new_seniority != current_seniority:
            seniority_extractor.update_job_seniority(job_id, description, engine)
            stats["seniority_updated"] += 1

        stats["jobs_processed"] += 1

    logger.info("pipeline_run_complete", **stats)
    return stats


def run_quality_checks(engine: Engine) -> dict:
    """Run data quality checks by querying the database.

    Calculates the necessary metrics and calls run_checks().
    If any check fails, a Telegram alert is sent automatically.

    Args:
        engine: SQLAlchemy engine connected to the target database.

    Returns:
        Result dict from run_checks() with checks_passed and failed_checks.
    """
    from scraper.quality.checks import run_checks

    with engine.begin() as conn:
        # Jobs scraped today
        today_jobs = conn.execute(
            text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE DATE(scraped_at) = CURRENT_DATE"
            )
        ).scalar()

        # Average daily job count over the last 7 days
        avg_7d = conn.execute(
            text(
                "SELECT COALESCE(AVG(cnt), 0) FROM ("
                "  SELECT COUNT(*) AS cnt FROM jobs "
                "  WHERE scraped_at >= CURRENT_DATE - INTERVAL '7 days' "
                "  GROUP BY DATE(scraped_at)"
                ") sub"
            )
        ).scalar()

        # Jobs today with empty or very short descriptions
        empty_desc = conn.execute(
            text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE DATE(scraped_at) = CURRENT_DATE "
                "AND LENGTH(COALESCE(description, '')) < 50"
            )
        ).scalar()

        # Total jobs scraped today
        total = conn.execute(
            text(
                "SELECT COUNT(*) FROM jobs "
                "WHERE DATE(scraped_at) = CURRENT_DATE"
            )
        ).scalar()

        # Sources that had new jobs today
        sources_result = conn.execute(
            text(
                "SELECT DISTINCT s.name FROM sources s "
                "JOIN jobs j ON j.source_id = s.id "
                "WHERE DATE(j.scraped_at) = CURRENT_DATE"
            )
        )
        sources_with_data = [row[0] for row in sources_result]

        # All active sources
        all_sources_result = conn.execute(
            text("SELECT name FROM sources WHERE active = TRUE")
        )
        all_sources = [row[0] for row in all_sources_result]

        # Jobs today without any linked technology
        no_tech = conn.execute(
            text(
                "SELECT COUNT(*) FROM jobs j "
                "LEFT JOIN job_technologies jt ON j.id = jt.job_id "
                "WHERE DATE(j.scraped_at) = CURRENT_DATE "
                "AND jt.job_id IS NULL"
            )
        ).scalar()

    return run_checks(
        jobs_today=today_jobs or 0,
        avg_7d=float(avg_7d or 0),
        empty_descriptions=empty_desc or 0,
        total=total or 0,
        sources_with_data=sources_with_data,
        all_sources=all_sources,
        jobs_without_tech=no_tech or 0,
    )


def run_pipeline_full(engine: Engine) -> dict:
    """Ejecuta pipeline completo: ETL + quality checks + snapshot.

    Alias para uso desde CLI cuando se quiere todo junto.

    Args:
        engine: SQLAlchemy engine connected to the target database.

    Returns:
        Dict con etl, quality_checks y snapshot.
    """
    # 1. ETL — procesar jobs sin tecnología linkada
    etl_stats = run_pipeline(engine)

    # 2. Quality checks
    checks_result = run_quality_checks(engine)

    # 3. Snapshot
    from analytics.snapshot_generator import generate

    snapshot = generate(engine)

    return {
        "etl": etl_stats,
        "quality_checks": checks_result,
        "snapshot": snapshot,
    }