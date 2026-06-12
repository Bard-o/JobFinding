"""Unit tests for the job extractor module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scraper.extractors.job_extractor import (
    extract_job,
    normalize_url,
)
from scraper.models import JobData

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestNormalizeUrl:
    """Test URL normalization (/empleos/ → /jobs/)."""

    def test_normalize_empleos_to_jobs(self) -> None:
        """Spanish /empleos/ path is replaced with /jobs/."""
        url = "https://www.getonboard.com/empleos/programming/react-dev"
        assert normalize_url(url) == "https://www.getonboard.com/jobs/programming/react-dev"

    def test_normalize_jobs_url_unchanged(self) -> None:
        """English /jobs/ URL is not modified."""
        url = "https://www.getonboard.com/jobs/programming/react-dev"
        assert normalize_url(url) == url

    def test_normalize_empleos_in_middle_of_url(self) -> None:
        """Only the path segment /empleos/ is replaced, not subdomains."""
        url = "https://www.getonboard.com/empleos/design/ux-lead"
        assert normalize_url(url) == "https://www.getonboard.com/jobs/design/ux-lead"

    def test_normalize_preserves_query_and_fragment(self) -> None:
        """Query strings and fragments are preserved after normalization."""
        url = "https://www.getonboard.com/empleos/dev?ref=home#apply"
        assert normalize_url(url) == "https://www.getonboard.com/jobs/dev?ref=home#apply"

    def test_normalize_url_without_empleos(self) -> None:
        """URLs that don't contain /empleos/ are returned as-is."""
        url = "https://www.getonboard.com/jobs/devops/sre"
        assert normalize_url(url) == url

    def test_normalize_empleos_non_overlapping(self) -> None:
        """str.replace is non-overlapping: /empleos/empleos/ only replaces the first
        occurrence because the trailing / of the first match and the leading /
        of the second are the same character. This is correct for real URLs
        which never have nested /empleos/ segments."""
        url = "https://www.getonboard.com/empleos/programming/dev"
        assert normalize_url(url) == "https://www.getonboard.com/jobs/programming/dev"
        # Edge case: consecutive /empleos/ shares a /, so only first is replaced
        edge = "https://www.getonboard.com/empleos/empleos/nested"
        assert normalize_url(edge) == "https://www.getonboard.com/jobs/empleos/nested"


class TestExtractJobCompleteFixture:
    """Test extract_job against the complete HTML fixture (all fields present)."""

    @pytest.fixture
    def complete_html(self) -> str:
        """Load the complete job detail HTML fixture."""
        return (FIXTURES_DIR / "sample_job_detail_complete.html").read_text()

    def test_extracts_title(self, complete_html: str) -> None:
        """Title is extracted from h1 tag."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.title == "Senior React Developer"

    def test_extracts_company(self, complete_html: str) -> None:
        """Company name is extracted from company-name span."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.company == "Acme Corp"

    def test_extracts_country(self, complete_html: str) -> None:
        """Country is extracted from itemprop meta tag."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.country == "Colombia"

    def test_extracts_published_at(self, complete_html: str) -> None:
        """Publication date is extracted from time@datetime attribute."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.published_at == date(2024, 1, 15)

    def test_extracts_work_type(self, complete_html: str) -> None:
        """Work type is extracted and normalized to lowercase."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.work_type == "remote"

    def test_extracts_seniority(self, complete_html: str) -> None:
        """Seniority is extracted from badge element."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.seniority == "senior"

    def test_extracts_salary(self, complete_html: str) -> None:
        """Salary string is extracted as-is from the salary-range span."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.salary_raw == "USD 5,000 - 7,000 / month"

    def test_extracts_description(self, complete_html: str) -> None:
        """Description is extracted from meta or div content."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert job.description is not None
        assert "React Developer" in job.description

    def test_extracts_tags(self, complete_html: str) -> None:
        """Technology tags are extracted from /jobs/tag/ links."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert "react" in job.tags
        assert "typescript" in job.tags
        assert "graphql" in job.tags
        assert len(job.tags) == 5

    def test_normalizes_empleos_url(self, complete_html: str) -> None:
        """URL is normalized (empleos → jobs) in the returned JobData."""
        job = extract_job(complete_html, "https://www.getonboard.com/empleos/programming/senior-react-developer")
        assert "/jobs/" in job.url
        assert "/empleos/" not in job.url

    def test_returns_job_data_instance(self, complete_html: str) -> None:
        """The returned object is a JobData instance."""
        job = extract_job(complete_html, "https://www.getonboard.com/jobs/programming/senior-react-developer")
        assert isinstance(job, JobData)


class TestExtractJobMinimalFixture:
    """Test extract_job against the minimal HTML fixture (only required fields)."""

    @pytest.fixture
    def minimal_html(self) -> str:
        """Load the minimal job detail HTML fixture."""
        return (FIXTURES_DIR / "sample_job_detail_minimal.html").read_text()

    def test_extracts_title_from_h1(self, minimal_html: str) -> None:
        """Title is extracted from h1 even without og:title."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert job.title == "Python Developer"

    def test_extracts_company(self, minimal_html: str) -> None:
        """Company name is extracted."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert job.company == "StartupXYZ"

    def test_extracts_country_from_text(self, minimal_html: str) -> None:
        """Country is extracted from text content (no itemprop meta)."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert job.country == "Argentina"

    def test_extracts_published_at_from_time_tag(self, minimal_html: str) -> None:
        """Publication date is extracted from time@datetime."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert job.published_at == date(2024, 2, 1)

    def test_extracts_tags_minimal(self, minimal_html: str) -> None:
        """Tags from /jobs/tag/ links are extracted."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert "python" in job.tags
        assert "django" in job.tags

    def test_missing_optional_fields_are_none(self, minimal_html: str) -> None:
        """Optional fields that are not present in HTML default to None."""
        job = extract_job(minimal_html, "https://www.getonboard.com/jobs/programming/python-dev")
        assert job.work_type is None
        assert job.seniority is None
        assert job.salary_raw is None


class TestExtractJobAllFieldsFixture:
    """Test extract_job against the fixture with all fields populated."""

    @pytest.fixture
    def all_fields_html(self) -> str:
        """Load the all-fields job detail HTML fixture."""
        return (FIXTURES_DIR / "sample_job_detail_all_fields.html").read_text()

    def test_extracts_title_with_lead(self, all_fields_html: str) -> None:
        """Title is extracted from h1 tag."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert job.title == "Lead Full Stack Engineer"

    def test_extracts_seniority_lead(self, all_fields_html: str) -> None:
        """Seniority 'Lead' is correctly mapped."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert job.seniority == "lead"

    def test_extracts_work_type_hybrid(self, all_fields_html: str) -> None:
        """Work type 'Hybrid' is correctly mapped."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert job.work_type == "hybrid"

    def test_extracts_country_with_flag_emoji(self, all_fields_html: str) -> None:
        """Country is extracted and flag emoji is stripped."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        # The HTML has 🇲🇽 Mexico, we should extract "Mexico"
        assert job.country == "Mexico"

    def test_extracts_salary_range(self, all_fields_html: str) -> None:
        """Salary range is extracted as raw text."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert job.salary_raw is not None
        assert "USD" in job.salary_raw or "8,000" in job.salary_raw

    def test_extracts_all_tags(self, all_fields_html: str) -> None:
        """All 8 technology tags are extracted."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert len(job.tags) == 8
        assert "python" in job.tags
        assert "kubernetes" in job.tags

    def test_extracts_published_at_from_time(self, all_fields_html: str) -> None:
        """Publication date is extracted correctly."""
        job = extract_job(all_fields_html, "https://www.getonboard.com/jobs/programming/lead-full-stack-engineer")
        assert job.published_at == date(2024, 3, 10)