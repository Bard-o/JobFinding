"""Unit tests for the CLI entry point (main module)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from scraper.main import SOURCES, DEFAULT_LIMIT, main, seed_source


class TestSeedSource:
    """Test source seeding in the database."""

    @patch("scraper.main.create_engine")
    def test_seed_source_inserts_new(self, mock_create_engine) -> None:
        """New source is inserted into the database."""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        seed_source(mock_engine, source_id=1, source_name="getonbrd",
                    base_url="https://www.getonbrd.com")

        mock_conn.execute.assert_called_once()

    @patch("scraper.main.create_engine")
    def test_seed_source_idempotent(self, mock_create_engine) -> None:
        """Seeding the same source twice does not fail (ON CONFLICT DO NOTHING)."""
        mock_conn = MagicMock()
        mock_engine = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        seed_source(mock_engine, source_id=1, source_name="getonbrd",
                    base_url="https://www.getonbrd.com")
        seed_source(mock_engine, source_id=1, source_name="getonbrd",
                    base_url="https://www.getonbrd.com")

        assert mock_conn.execute.call_count == 2


class TestSources:
    """Test the SOURCES mapping."""

    def test_getonbrd_source_exists(self) -> None:
        """GetOnBoard (getonbrd) source is defined."""
        assert "getonbrd" in SOURCES
        assert SOURCES["getonbrd"] == 1

    def test_default_limit(self) -> None:
        """Default limit is 50."""
        assert DEFAULT_LIMIT == 50


class TestMainCLI:
    """Test the main CLI entry point."""

    @patch("scraper.main.fetch_jobs")
    @patch("scraper.main.run_etl")
    @patch("scraper.main.seed_source")
    @patch("scraper.main.create_engine")
    @patch("scraper.main.Settings.from_env")
    def test_main_with_limit(
        self, mock_settings, mock_create_engine, mock_seed,
        mock_etl, mock_fetch_jobs,
    ) -> None:
        """Main runs the pipeline with --limit using the API."""
        from scraper.models import JobData

        mock_settings.return_value = MagicMock(
            database_url="sqlite:///:memory:",
            telegram_bot_token=None,
            telegram_chat_id=None,
        )
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # API returns mock jobs
        mock_jobs = [
            JobData(
                title="Software Engineer",
                company="TestCorp",
                url="https://www.getonbrd.com/jobs/test-1",
                published_at=date(2026, 1, 15),
                country="Chile",
                work_type="remote",
                seniority="senior",
                salary_raw=None,
                description="<p>Test description</p>",
                tags=["python", "react"],
            ),
        ]
        mock_fetch_jobs.return_value = iter(mock_jobs)

        # ETL returns stats
        mock_etl.return_value = {
            "inserted_jobs": 1, "existing_jobs": 0,
            "skipped_invalid": 0, "companies_upserted": 1,
            "tech_links_created": 2,
        }

        exit_code = main(["--source", "getonbrd", "--limit", "5"])

        assert exit_code == 0
        mock_fetch_jobs.assert_called_once()
        mock_etl.assert_called_once()

    @patch("scraper.main.fetch_jobs")
    @patch("scraper.main.seed_source")
    @patch("scraper.main.create_engine")
    @patch("scraper.main.Settings.from_env")
    def test_main_empty_api(
        self, mock_settings, mock_create_engine, mock_seed,
        mock_fetch_jobs,
    ) -> None:
        """Main handles empty API response gracefully."""
        mock_settings.return_value = MagicMock(
            database_url="sqlite:///:memory:",
            telegram_bot_token=None,
            telegram_chat_id=None,
        )
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_fetch_jobs.return_value = iter([])

        exit_code = main(["--source", "getonbrd", "--limit", "10"])

        assert exit_code == 0

    def test_main_invalid_source(self) -> None:
        """Main exits with error for invalid source."""
        with pytest.raises(SystemExit):
            main(["--source", "invalid_source"])

    @patch("scraper.main.Settings.from_env")
    def test_main_config_error(self, mock_settings) -> None:
        """Main exits with error when DATABASE_URL is not set."""
        mock_settings.side_effect = ValueError("DATABASE_URL required")

        exit_code = main(["--source", "getonbrd", "--limit", "5"])

        assert exit_code == 1