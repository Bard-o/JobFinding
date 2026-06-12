"""CLI entry point for the JobFinding scrapers.

Usage::

    python -m scraper --source getonbrd --limit 50
    python -m scraper --source remotive --limit 100

Orchestrates: source seeding → job fetching → ETL pipeline → failure alerting.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

import structlog
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env file before any other imports that read env vars
load_dotenv()

from scraper.alerts.telegram import send_alert
from scraper.api import fetch_jobs
from scraper.config import Settings
from scraper.etl.pipeline import run_etl
from scraper.models import JobData

logger = structlog.get_logger(__name__)

# Supported sources and their IDs in the database
SOURCES: dict[str, int] = {
    "getonbrd": 1,   # getonbrd.com (formerly getonboard)
    "remotive": 2,    # remotive.com
}

# Base URLs for each source (used for seeding)
SOURCE_URLS: dict[str, str] = {
    "getonbrd": "https://www.getonbrd.com",
    "remotive": "https://remotive.com",
}

DEFAULT_LIMIT = 50


def seed_source(engine, source_id: int, source_name: str, base_url: str) -> None:
    """Ensure the source exists in the database before inserting jobs.

    Args:
        engine: SQLAlchemy engine.
        source_id: The source ID to seed.
        source_name: The source name (e.g. 'getonbrd').
        base_url: The base URL for the source.
    """
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO sources (id, name, base_url, active) "
                "VALUES (:id, :name, :url, TRUE) "
                "ON CONFLICT (name) DO UPDATE SET base_url = :url"
            ),
            {"id": source_id, "name": source_name, "url": base_url},
        )
    logger.info("source_seeded", source_name=source_name, source_id=source_id)


def main(argv: Optional[list[str]] = None) -> int:
    """Run the scraper pipeline from the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = argparse.ArgumentParser(
        description="JobFinding scraper — downloads and processes job listings.",
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=list(SOURCES.keys()),
        help="Data source to scrape (getonbrd, remotive).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max jobs to collect (0 for full scrape, default: {DEFAULT_LIMIT}).",
    )
    args = parser.parse_args(argv)

    # Configure structlog for console output
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    source_name = args.source
    source_id = SOURCES[source_name]
    limit = args.limit if args.limit > 0 else None  # 0 means no limit

    logger.info(
        "scraper_start",
        source=source_name,
        source_id=source_id,
        limit=limit or "unlimited",
    )

    try:
        settings = Settings.from_env()
    except ValueError as e:
        logger.error("config_error", error=str(e))
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    engine = create_engine(settings.database_url)

    # Step 1: Seed the source in the database
    try:
        seed_source(
            engine,
            source_id=source_id,
            source_name=source_name,
            base_url=SOURCE_URLS[source_name],
        )
    except Exception as e:
        logger.error("source_seed_failed", error=str(e))
        send_alert(f"🔴 {source_name} scraper: failed to seed source — {e}")
        return 1

    # Step 2: Fetch jobs from the appropriate source
    jobs: list[JobData] = []

    try:
        if source_name == "getonbrd":
            for i, job in enumerate(fetch_jobs(country_code="CL", per_page=120), 1):
                if limit and i > limit:
                    break
                jobs.append(job)
                if i % 10 == 0:
                    logger.info("api_progress", processed=i, collected=len(jobs))
        elif source_name == "remotive":
            from scraper.scrapers.remotive import RemotiveScraper

            scraper = RemotiveScraper(limit=limit or 100)
            jobs = scraper.run()
    except Exception as e:
        logger.error("fetch_failed", source=source_name, error=str(e))
        send_alert(f"🔴 {source_name} scraper: fetch failed — {e}")
        return 1

    logger.info(
        "fetch_complete",
        source=source_name,
        jobs_collected=len(jobs),
    )

    # Step 3: Run ETL pipeline
    if not jobs:
        logger.warning("no_jobs_collected", source=source_name)
        send_alert(
            f"⚠️ {source_name} scraper: zero jobs collected. "
            f"Check API access or rate limiting."
        )
        return 0

    try:
        stats = run_etl(jobs, engine, source_id=source_id)
    except Exception as e:
        logger.error("etl_failed", error=str(e))
        send_alert(f"🔴 {source_name} scraper: ETL pipeline failed — {e}")
        return 1

    logger.info("scraper_complete", source=source_name, **stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())