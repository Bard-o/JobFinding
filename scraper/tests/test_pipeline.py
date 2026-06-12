"""Unit tests for the ETL pipeline module."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

from scraper.etl.pipeline import (
    BATCH_SIZE,
    REQUIRED_FIELDS,
    _insert_jobs,
    _is_valid_job,
    _link_technologies,
    _upsert_companies,
    run_etl,
)
from scraper.models import JobData


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_jobs() -> list[JobData]:
    """A list of valid JobData objects for testing."""
    return [
        JobData(
            title="React Developer",
            company="Acme Corp",
            url="https://www.getonboard.com/jobs/programming/react-dev",
            published_at=date(2024, 1, 15),
            country="Argentina",
            work_type="remote",
            seniority="senior",
            salary_raw="$5000-7000 USD/mo",
            description="Build amazing things with React.",
            tags=["react", "javascript"],
        ),
        JobData(
            title="Python Engineer",
            company="TechGlobal",
            url="https://www.getonboard.com/jobs/programming/python-dev",
            published_at=date(2024, 1, 10),
            country="Mexico",
            work_type="hybrid",
            seniority="mid",
            salary_raw=None,
            description="Backend development with Python.",
            tags=["python", "django"],
        ),
    ]


@pytest.fixture
def engine():
    """In-memory SQLite engine with schema pre-created."""
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE sources (id INTEGER PRIMARY KEY, name VARCHAR(100) "
            "UNIQUE NOT NULL, base_url TEXT NOT NULL, active BOOLEAN DEFAULT TRUE, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE companies (id INTEGER PRIMARY KEY, name VARCHAR(255) "
            "UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE jobs (id INTEGER PRIMARY KEY, source_id INTEGER NOT "
            "NULL REFERENCES sources(id), company_id INTEGER REFERENCES "
            "companies(id), title VARCHAR(255) NOT NULL, country VARCHAR(100), "
            "published_at DATE, url TEXT NOT NULL UNIQUE, work_type VARCHAR(20), "
            "description TEXT, salary_raw TEXT, seniority VARCHAR(20), "
            "scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE technologies (id INTEGER PRIMARY KEY, name "
            "VARCHAR(100) NOT NULL UNIQUE, category VARCHAR(50) NOT NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ))
        conn.execute(text(
            "CREATE TABLE job_technologies (job_id INTEGER NOT NULL REFERENCES "
            "jobs(id) ON DELETE CASCADE, technology_id INTEGER NOT NULL REFERENCES "
            "technologies(id), PRIMARY KEY (job_id, technology_id))"
        ))
        # Seed source and technologies
        conn.execute(text(
            "INSERT INTO sources (id, name, base_url, active) VALUES "
            "(1, 'getonboard', 'https://www.getonboard.com', 1)"
        ))
        conn.execute(text(
            "INSERT INTO technologies (name, category) VALUES "
            "('React', 'framework'), ('JavaScript', 'language'), "
            "('Python', 'language'), ('Django', 'framework')"
        ))
    return eng


# ── Data Quality Validation Tests ─────────────────────────────────────────


class TestIsValidJob:
    """Test _is_valid_job rejects jobs missing required fields."""

    def test_valid_job(self) -> None:
        """A job with all required fields is valid."""
        job = JobData(
            title="Dev", company="Corp", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is True

    def test_missing_title(self) -> None:
        """A job with empty title is invalid."""
        job = JobData(
            title="", company="Corp", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is False

    def test_missing_company(self) -> None:
        """A job with empty company is invalid."""
        job = JobData(
            title="Dev", company="", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is False

    def test_missing_url(self) -> None:
        """A job with empty url is invalid."""
        job = JobData(
            title="Dev", company="Corp", url="",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is False

    def test_missing_published_at(self) -> None:
        """A job with None published_at is invalid."""
        job = JobData(
            title="Dev", company="Corp", url="https://example.com/jobs/1",
            published_at=None,
        )
        assert _is_valid_job(job) is False

    def test_whitespace_only_title(self) -> None:
        """A job with whitespace-only title is invalid."""
        job = JobData(
            title="   ", company="Corp", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is False

    def test_whitespace_only_company(self) -> None:
        """A job with whitespace-only company is invalid."""
        job = JobData(
            title="Dev", company="   ", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        assert _is_valid_job(job) is False

    def test_optional_fields_can_be_none(self) -> None:
        """A job with None optional fields (country, salary, etc.) is valid."""
        job = JobData(
            title="Dev", company="Corp", url="https://example.com/jobs/1",
            published_at=date(2024, 1, 1), country=None, salary_raw=None,
            description=None, work_type=None, seniority=None,
        )
        assert _is_valid_job(job) is True


# ── Company Upsert Tests ──────────────────────────────────────────────────


class TestUpsertCompanies:
    """Test _upsert_companies creates and deduplicates companies."""

    def test_insert_new_companies(self, engine, sample_jobs) -> None:
        """New companies are inserted and their IDs returned."""
        company_ids = _upsert_companies(sample_jobs, engine)
        assert "Acme Corp" in company_ids
        assert "TechGlobal" in company_ids
        assert len(company_ids) == 2

        # Verify rows in DB
        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM companies"))
            assert result.fetchone()[0] == 2

    def test_upsert_existing_companies(self, engine, sample_jobs) -> None:
        """Upserting the same company names returns existing IDs."""
        # First insert
        ids1 = _upsert_companies(sample_jobs, engine)
        # Second upsert (same names)
        ids2 = _upsert_companies(sample_jobs, engine)
        assert ids1["Acme Corp"] == ids2["Acme Corp"]
        assert ids1["TechGlobal"] == ids2["TechGlobal"]

        # No new rows
        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM companies"))
            assert result.fetchone()[0] == 2

    def test_deduplicate_same_company(self, engine) -> None:
        """Multiple jobs from the same company produce only one company row."""
        jobs = [
            JobData(title="Dev1", company="Acme", url="https://ex.com/jobs/1",
                    published_at=date(2024, 1, 1)),
            JobData(title="Dev2", company="Acme", url="https://ex.com/jobs/2",
                    published_at=date(2024, 1, 2)),
        ]
        company_ids = _upsert_companies(jobs, engine)
        assert len(company_ids) == 1
        assert "Acme" in company_ids


# ── Job Insert Tests ──────────────────────────────────────────────────────


class TestInsertJobs:
    """Test _insert_jobs with ON CONFLICT (url) DO NOTHING."""

    def test_insert_new_jobs(self, engine, sample_jobs) -> None:
        """New jobs are inserted successfully."""
        company_ids = _upsert_companies(sample_jobs, engine)
        inserted, existing = _insert_jobs(
            sample_jobs, company_ids, engine, source_id=1
        )
        assert inserted == 2
        assert existing == 0

        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM jobs"))
            assert result.fetchone()[0] == 2

    def test_duplicate_url_skipped(self, engine, sample_jobs) -> None:
        """Jobs with duplicate URLs are silently skipped (DO NOTHING)."""
        company_ids = _upsert_companies(sample_jobs, engine)
        # First insert
        _insert_jobs(sample_jobs, company_ids, engine, source_id=1)
        # Second insert — same URLs should be skipped
        inserted, existing = _insert_jobs(
            sample_jobs, company_ids, engine, source_id=1
        )
        assert inserted == 0
        assert existing == 2

        # Still only 2 rows, not 4
        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM jobs"))
            assert result.fetchone()[0] == 2

    def test_insert_with_none_optional_fields(self, engine) -> None:
        """Jobs with None optional fields insert correctly."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), country=None,
            work_type=None, seniority=None, salary_raw=None,
            description=None, tags=[],
        )
        company_ids = _upsert_companies([job], engine)
        inserted, existing = _insert_jobs(
            [job], company_ids, engine, source_id=1
        )
        assert inserted == 1

        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT country, work_type, seniority FROM jobs WHERE url = :url"),
                {"url": "https://ex.com/jobs/1"},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] is None  # country
            assert row[1] is None  # work_type
            assert row[2] is None  # seniority


# ── Technology Linking Tests ──────────────────────────────────────────────


class TestLinkTechnologies:
    """Test _link_technologies resolves tags and creates associations."""

    def test_link_known_tags(self, engine, sample_jobs) -> None:
        """Known technology tags are linked to jobs."""
        company_ids = _upsert_companies(sample_jobs, engine)
        _insert_jobs(sample_jobs, company_ids, engine, source_id=1)

        links = _link_technologies(sample_jobs, engine)
        # react → React (1), javascript → JavaScript (1),
        # python → Python (1), django → Django (1)
        assert links == 4

        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM job_technologies"))
            assert result.fetchone()[0] == 4

    def test_unknown_tags_skipped(self, engine) -> None:
        """Unknown tags are silently skipped with a debug log."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), tags=["unknown-tech"],
        )
        company_ids = _upsert_companies([job], engine)
        _insert_jobs([job], company_ids, engine, source_id=1)

        links = _link_technologies([job], engine)
        assert links == 0  # unknown-tech not in technologies table

    def test_case_insensitive_tag_matching(self, engine) -> None:
        """Tag matching is case-insensitive (react → React)."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), tags=["react"],
        )
        company_ids = _upsert_companies([job], engine)
        _insert_jobs([job], company_ids, engine, source_id=1)

        links = _link_technologies([job], engine)
        assert links == 1  # "react" matches "React"

    def test_no_tags_no_links(self, engine) -> None:
        """Jobs without tags create no technology links."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), tags=[],
        )
        company_ids = _upsert_companies([job], engine)
        _insert_jobs([job], company_ids, engine, source_id=1)

        links = _link_technologies([job], engine)
        assert links == 0


# ── Full Pipeline Tests ──────────────────────────────────────────────────


class TestRunEtl:
    """Test the full run_etl pipeline."""

    @patch("scraper.etl.pipeline.send_alert")
    def test_full_pipeline_happy_path(
        self, mock_alert, engine, sample_jobs
    ) -> None:
        """Full pipeline inserts jobs, companies, and tech links."""
        stats = run_etl(sample_jobs, engine, source_id=1)

        assert stats["inserted_jobs"] == 2
        assert stats["existing_jobs"] == 0
        assert stats["skipped_invalid"] == 0
        assert stats["companies_upserted"] == 2
        assert stats["tech_links_created"] == 4
        assert mock_alert.call_count == 0

    @patch("scraper.etl.pipeline.send_alert")
    def test_pipeline_skips_invalid_jobs(self, mock_alert, engine) -> None:
        """Invalid jobs are skipped and counted."""
        invalid_job = JobData(
            title="", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1),
        )
        valid_job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/2",
            published_at=date(2024, 1, 1),
        )
        stats = run_etl([invalid_job, valid_job], engine, source_id=1)

        assert stats["skipped_invalid"] == 1
        assert stats["inserted_jobs"] == 1

    @patch("scraper.etl.pipeline.send_alert")
    def test_pipeline_deduplicates_urls(self, mock_alert, engine) -> None:
        """Running pipeline twice doesn't duplicate jobs."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), tags=[],
        )
        run_etl([job], engine, source_id=1)
        stats = run_etl([job], engine, source_id=1)

        assert stats["inserted_jobs"] == 0
        assert stats["existing_jobs"] == 1

    @patch("scraper.etl.pipeline.send_alert")
    def test_pipeline_all_invalid_sends_alert(self, mock_alert, engine) -> None:
        """If all jobs are invalid, an alert is sent."""
        invalid_job = JobData(
            title="", company="", url="", published_at=None,
        )
        stats = run_etl([invalid_job], engine, source_id=1)

        assert stats["skipped_invalid"] == 1
        assert mock_alert.call_count == 1
        assert "invalid" in mock_alert.call_args[0][0].lower()

    @patch("scraper.etl.pipeline.send_alert")
    def test_pipeline_zero_inserts_alerts(self, mock_alert, engine) -> None:
        """If all valid jobs already exist in DB, an alert is sent."""
        job = JobData(
            title="Dev", company="Corp", url="https://ex.com/jobs/1",
            published_at=date(2024, 1, 1), tags=[],
        )
        # First run: inserts
        run_etl([job], engine, source_id=1)
        mock_alert.reset_mock()

        # Second run: all already exist
        stats = run_etl([job], engine, source_id=1)
        assert stats["inserted_jobs"] == 0
        assert stats["existing_jobs"] == 1
        assert mock_alert.call_count == 1