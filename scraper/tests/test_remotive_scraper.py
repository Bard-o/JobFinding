"""Tests para Remotive scraper."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from scraper.scrapers.remotive import (
    LATAM_KEYWORDS,
    REMOTIVE_API_URL,
    RemotiveScraper,
    _clean_description,
    _job_from_json,
    _normalize_work_type,
    _parse_date,
    fetch_jobs,
    is_latam,
)


class TestIsLatam:
    """Test LATAM location filtering."""

    def test_latam_countries(self) -> None:
        assert is_latam("LATAM") is True
        assert is_latam("Argentina") is True
        assert is_latam("Brasil") is True
        assert is_latam("Chile") is True
        assert is_latam("Colombia") is True
        assert is_latam("Mexico") is True
        assert is_latam("South America") is True

    def test_remote_worldwide(self) -> None:
        assert is_latam("Remote") is True
        assert is_latam("Worldwide") is True
        assert is_latam("Anywhere") is True

    def test_non_latam_rejected(self) -> None:
        assert is_latam("USA") is False
        assert is_latam("Europe") is False
        assert is_latam("Asia") is False
        assert is_latam("California") is False

    def test_none_returns_false(self) -> None:
        assert is_latam(None) is False

    def test_empty_string_returns_false(self) -> None:
        assert is_latam("") is False

    def test_partial_match(self) -> None:
        assert is_latam("Latin America / Worldwide") is True
        assert is_latam("Remote - Latin America") is True


class TestNormalizeWorkType:
    """Test work type normalization from Remotive job types."""

    def test_full_time_remote_location(self) -> None:
        assert _normalize_work_type("full_time", "Remote") == "remote"
        assert _normalize_work_type("full_time", "Worldwide") == "remote"
        assert _normalize_work_type("full_time", "Anywhere") == "remote"

    def test_full_time_with_specific_location(self) -> None:
        assert _normalize_work_type("full_time", "Argentina") == "onsite"
        assert _normalize_work_type("full_time", "Brasil") == "onsite"

    def test_full_time_with_no_location(self) -> None:
        assert _normalize_work_type("full_time", None) == "remote"

    def test_other_job_types(self) -> None:
        assert _normalize_work_type("contract", "Argentina") == "contract"
        assert _normalize_work_type("part_time", "Argentina") == "part_time"
        assert _normalize_work_type("freelance", "Argentina") == "freelance"
        assert _normalize_work_type("internship", "Argentina") == "internship"

    def test_unknown_job_type_defaults_to_onsite(self) -> None:
        assert _normalize_work_type("unknown_type", "Argentina") == "onsite"

    def test_full_time_remote_in_location_string(self) -> None:
        assert _normalize_work_type("full_time", "Remote, Latin America") == "remote"
        assert _normalize_work_type("full_time", "Worldwide remote") == "remote"


class TestParseDate:
    """Test Remotive date parsing."""

    def test_valid_datetime_with_z(self) -> None:
        result = _parse_date("2024-01-15T00:00:00Z")
        assert result == date(2024, 1, 15)

    def test_valid_datetime_with_offset(self) -> None:
        result = _parse_date("2024-01-15T10:30:00+03:00")
        assert result == date(2024, 1, 15)

    def test_valid_date_only(self) -> None:
        result = _parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_none_returns_none(self) -> None:
        assert _parse_date(None) is None

    def test_invalid_returns_none(self) -> None:
        assert _parse_date("invalid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _parse_date("") is None


class TestCleanDescription:
    """Test HTML description cleaning."""

    def test_strips_html_tags(self) -> None:
        result = _clean_description("<p>Python developer role</p>")
        assert result == "Python developer role"

    def test_handles_multiple_tags(self) -> None:
        result = _clean_description("<div><p>We need <b>Python</b> devs</p></div>")
        assert "Python" in result
        assert "devs" in result

    def test_empty_string(self) -> None:
        assert _clean_description("") == ""

    def test_plain_text_passthrough(self) -> None:
        result = _clean_description("Just plain text")
        assert result == "Just plain text"


class TestJobFromJson:
    """Test conversion from Remotive JSON to JobData."""

    def test_latam_job_converted(self) -> None:
        raw = {
            "title": "Python Developer",
            "company_name": "TechCorp",
            "url": "https://remotive.com/job/123",
            "publication_date": "2024-01-15T00:00:00Z",
            "candidate_required_location": "LATAM",
            "job_type": "full_time",
            "description": "<p>Python developer role</p>",
            "tags": ["python", "django"],
        }
        job = _job_from_json(raw)
        assert job is not None
        assert job.title == "Python Developer"
        assert job.company == "TechCorp"
        assert job.url == "https://remotive.com/job/123"
        assert job.published_at == date(2024, 1, 15)
        assert job.country == "LATAM"
        assert job.work_type == "remote"
        assert job.tags == ["python", "django"]
        assert job.seniority is None
        assert job.salary_raw is None

    def test_remote_location_classified_as_remote(self) -> None:
        raw = {
            "title": "DevOps Engineer",
            "company_name": "CloudCo",
            "url": "https://remotive.com/job/456",
            "publication_date": "2024-02-01T00:00:00Z",
            "candidate_required_location": "Remote",
            "job_type": "full_time",
            "description": "",
            "tags": [],
        }
        job = _job_from_json(raw)
        assert job is not None
        assert job.work_type == "remote"

    def test_non_latam_returns_none(self) -> None:
        raw = {
            "title": "Python Developer",
            "company_name": "TechCorp",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": "USA",
        }
        assert _job_from_json(raw) is None

    def test_missing_title_returns_none(self) -> None:
        raw = {
            "title": "",
            "company_name": "TechCorp",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": "LATAM",
        }
        assert _job_from_json(raw) is None

    def test_missing_company_returns_none(self) -> None:
        raw = {
            "title": "Python Dev",
            "company_name": "",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": "LATAM",
        }
        assert _job_from_json(raw) is None

    def test_missing_url_returns_none(self) -> None:
        raw = {
            "title": "Python Dev",
            "company_name": "TechCorp",
            "url": "",
            "candidate_required_location": "LATAM",
        }
        assert _job_from_json(raw) is None

    def test_empty_location_returns_none(self) -> None:
        raw = {
            "title": "Python Dev",
            "company_name": "TechCorp",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": "",
        }
        assert _job_from_json(raw) is None

    def test_none_location_returns_none(self) -> None:
        raw = {
            "title": "Python Dev",
            "company_name": "TechCorp",
            "url": "https://remotive.com/job/123",
            "candidate_required_location": None,
        }
        assert _job_from_json(raw) is None

    def test_contract_job_type(self) -> None:
        raw = {
            "title": "Contract Dev",
            "company_name": "Acme",
            "url": "https://remotive.com/job/789",
            "publication_date": "2024-03-01",
            "candidate_required_location": "Argentina",
            "job_type": "contract",
            "description": "",
            "tags": [],
        }
        job = _job_from_json(raw)
        assert job is not None
        assert job.work_type == "contract"

    def test_no_tags_defaults_to_empty_list(self) -> None:
        raw = {
            "title": "Dev",
            "company_name": "Co",
            "url": "https://remotive.com/job/1",
            "candidate_required_location": "LATAM",
            "job_type": "full_time",
            "description": "",
            "tags": None,
        }
        job = _job_from_json(raw)
        assert job is not None
        assert job.tags == []

    def test_no_publication_date(self) -> None:
        raw = {
            "title": "Dev",
            "company_name": "Co",
            "url": "https://remotive.com/job/1",
            "publication_date": None,
            "candidate_required_location": "LATAM",
            "job_type": "full_time",
            "description": "",
            "tags": [],
        }
        job = _job_from_json(raw)
        assert job is not None
        assert job.published_at is None


class TestRemotiveScraper:
    """Test the RemotiveScraper class."""

    @patch("scraper.scrapers.remotive.fetch_jobs")
    def test_run_returns_jobs(self, mock_fetch: MagicMock) -> None:
        from scraper.models import JobData

        mock_jobs = [
            JobData(
                title="Dev",
                company="Co",
                url="https://remotive.com/job/1",
                published_at=date(2024, 1, 1),
                country="LATAM",
                work_type="remote",
            ),
        ]
        mock_fetch.return_value = mock_jobs
        scraper = RemotiveScraper(limit=50)
        result = scraper.run()
        assert result == mock_jobs
        mock_fetch.assert_called_once_with(limit=50)

    @patch("scraper.scrapers.remotive.fetch_jobs")
    def test_default_limit(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = []
        scraper = RemotiveScraper()
        scraper.run()
        mock_fetch.assert_called_once_with(limit=100)


class TestFetchJobs:
    """Test the fetch_jobs function with mocked HTTP."""

    @patch("scraper.scrapers.remotive.requests.get")
    def test_fetch_jobs_returns_latam_jobs(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobs": [
                {
                    "title": "Python Dev",
                    "company_name": "TechCorp",
                    "url": "https://remotive.com/job/1",
                    "publication_date": "2024-01-15T00:00:00Z",
                    "candidate_required_location": "LATAM",
                    "job_type": "full_time",
                    "description": "<p>Python role</p>",
                    "tags": ["python"],
                },
                {
                    "title": "Java Dev",
                    "company_name": "EuroCorp",
                    "url": "https://remotive.com/job/2",
                    "publication_date": "2024-01-16T00:00:00Z",
                    "candidate_required_location": "Europe",
                    "job_type": "full_time",
                    "description": "<p>Java role</p>",
                    "tags": ["java"],
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        jobs = fetch_jobs(limit=100)

        assert len(jobs) == 1
        assert jobs[0].title == "Python Dev"
        assert jobs[0].country == "LATAM"
        mock_get.assert_called_once()

    @patch("scraper.scrapers.remotive.requests.get")
    def test_fetch_jobs_handles_api_error(self, mock_get: MagicMock) -> None:
        import requests as req

        mock_get.side_effect = req.RequestException("Connection error")
        jobs = fetch_jobs()
        assert jobs == []

    @patch("scraper.scrapers.remotive.requests.get")
    def test_fetch_jobs_empty_response(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        jobs = fetch_jobs()
        assert jobs == []