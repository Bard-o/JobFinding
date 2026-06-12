"""Tests para snapshot_generator."""

from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import create_engine, text

from analytics.snapshot_generator import (
    _get_jobs_by_seniority,
    _get_jobs_by_source,
    _get_jobs_by_work_type,
    _get_total_companies,
    _get_total_jobs,
    _get_top_technologies,
    generate,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def engine():
    """In-memory SQLite engine with schema pre-created."""
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE sources (id INTEGER PRIMARY KEY, name VARCHAR(100) "
                "UNIQUE NOT NULL, base_url TEXT NOT NULL, active BOOLEAN DEFAULT TRUE, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE companies (id INTEGER PRIMARY KEY, name VARCHAR(255) "
                "UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE jobs (id INTEGER PRIMARY KEY, source_id INTEGER NOT "
                "NULL REFERENCES sources(id), company_id INTEGER REFERENCES "
                "companies(id), title VARCHAR(255) NOT NULL, country VARCHAR(100), "
                "published_at DATE, url TEXT NOT NULL UNIQUE, work_type VARCHAR(20), "
                "description TEXT, salary_raw TEXT, seniority VARCHAR(20), "
                "scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE technologies (id INTEGER PRIMARY KEY, name "
                "VARCHAR(100) NOT NULL UNIQUE, category VARCHAR(50) NOT NULL, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE job_technologies (job_id INTEGER NOT NULL REFERENCES "
                "jobs(id) ON DELETE CASCADE, technology_id INTEGER NOT NULL REFERENCES "
                "technologies(id), PRIMARY KEY (job_id, technology_id))"
            )
        )
        # SQLite doesn't have JSONB — use TEXT for JSON storage
        conn.execute(
            text(
                "CREATE TABLE daily_snapshots (id INTEGER PRIMARY KEY, "
                "snapshot_date DATE NOT NULL UNIQUE, total_jobs INTEGER NOT NULL, "
                "total_companies INTEGER NOT NULL, jobs_by_source TEXT, "
                "jobs_by_seniority TEXT, jobs_by_work_type TEXT, "
                "top_technologies TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        # Seed data
        conn.execute(
            text(
                "INSERT INTO sources (id, name, base_url, active) VALUES "
                "(1, 'getonboard', 'https://www.getonboard.com', 1), "
                "(2, 'remotive', 'https://remotive.com', 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO companies (id, name) VALUES "
                "(1, 'Acme'), (2, 'TechCorp')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO jobs (id, source_id, company_id, title, url, "
                "published_at, work_type, seniority) VALUES "
                "(1, 1, 1, 'Python Dev', 'https://ex.com/1', '2024-01-15', "
                "'remote', 'senior'), "
                "(2, 1, 2, 'React Dev', 'https://ex.com/2', '2024-01-15', "
                "'hybrid', 'mid'), "
                "(3, 2, 1, 'Go Dev', 'https://ex.com/3', '2024-01-15', "
                "'remote', 'junior')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO technologies (id, name, category) VALUES "
                "(1, 'Python', 'language'), (2, 'React', 'framework'), "
                "(3, 'Go', 'language')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO job_technologies (job_id, technology_id) VALUES "
                "(1, 1), (1, 2), (2, 2), (3, 3)"
            )
        )
    return eng


# ── Helper function tests ──────────────────────────────────────────────────


class TestGetTotalJobs:
    def test_returns_count(self, engine) -> None:
        with engine.begin() as conn:
            assert _get_total_jobs(conn) == 3


class TestGetTotalCompanies:
    def test_returns_count(self, engine) -> None:
        with engine.begin() as conn:
            assert _get_total_companies(conn) == 2


class TestGetJobsBySource:
    def test_returns_dict_with_counts(self, engine) -> None:
        with engine.begin() as conn:
            result = _get_jobs_by_source(conn)
        assert result["getonboard"] == 2
        assert result["remotive"] == 1


class TestGetJobsBySeniority:
    def test_returns_dict_with_counts(self, engine) -> None:
        with engine.begin() as conn:
            result = _get_jobs_by_seniority(conn)
        assert result["senior"] == 1
        assert result["mid"] == 1
        assert result["junior"] == 1


class TestGetJobsByWorkType:
    def test_returns_dict_with_counts(self, engine) -> None:
        with engine.begin() as conn:
            result = _get_jobs_by_work_type(conn)
        assert result["remote"] == 2
        assert result["hybrid"] == 1


class TestGetTopTechnologies:
    def test_returns_sorted_by_count(self, engine) -> None:
        with engine.begin() as conn:
            result = _get_top_technologies(conn, limit=10)
        assert len(result) == 3
        # React appears in 2 jobs, Python and Go in 1 each
        assert result[0]["name"] == "React"
        assert result[0]["count"] == 2
        assert result[1]["name"] in ("Python", "Go")
        assert result[2]["name"] in ("Python", "Go")

    def test_respects_limit(self, engine) -> None:
        with engine.begin() as conn:
            result = _get_top_technologies(conn, limit=2)
        assert len(result) == 2


# ── Full generate() tests ─────────────────────────────────────────────────


class TestGenerate:
    def test_generates_snapshot(self, engine) -> None:
        result = generate(engine)

        assert result["snapshot_date"] == date.today().isoformat()
        assert result["total_jobs"] == 3
        assert result["total_companies"] == 2
        assert result["jobs_by_source"]["getonboard"] == 2
        assert result["jobs_by_source"]["remotive"] == 1
        assert result["jobs_by_seniority"]["senior"] == 1
        assert len(result["top_technologies"]) == 3

    def test_idempotent_updates_existing(self, engine) -> None:
        today = date.today()

        # First generation
        result1 = generate(engine)
        assert result1["total_jobs"] == 3

        # Second generation same day should update, not insert
        result2 = generate(engine)
        assert result2["total_jobs"] == 3

        # Only one row in daily_snapshots for today
        with engine.begin() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM daily_snapshots "
                    "WHERE snapshot_date = :today"
                ),
                {"today": today},
            ).scalar()
        assert count == 1

    def test_stores_json_correctly(self, engine) -> None:
        today = date.today()
        generate(engine)

        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT jobs_by_source, top_technologies FROM "
                    "daily_snapshots WHERE snapshot_date = :today"
                ),
                {"today": today},
            ).fetchone()

            # JSON strings stored in TEXT/JSONB — parse back to Python
            jbs = json.loads(row[0])
            assert isinstance(jbs, dict)
            assert jbs["getonboard"] == 2

            top_tech = json.loads(row[1])
            assert isinstance(top_tech, list)
            assert top_tech[0]["name"] == "React"