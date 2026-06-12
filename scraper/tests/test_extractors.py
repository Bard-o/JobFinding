"""Tests para tech_extractor y seniority_extractor."""

from __future__ import annotations

import pytest

from scraper.extractors.seniority_extractor import extract_seniority_from_text
from scraper.extractors.tech_extractor import extract_technologies_from_text


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _populate_tech_cache():
    """Puebla _tech_cache con tecnologías de ejemplo antes de cada test."""
    import scraper.extractors.tech_extractor as te

    # Simular el cache con tecnologías de la DB (name_lower -> id)
    te._tech_cache = {
        "python": 1,
        "javascript": 2,
        "typescript": 3,
        "react": 4,
        "django": 5,
        "postgresql": 6,
        "docker": 7,
        "java": 8,
        "go": 9,
        "rust": 10,
    }
    te._cache_loaded = True
    yield
    # Limpiar cache después del test
    te._tech_cache = {}
    te._cache_loaded = False


# ── Tests: extract_technologies_from_text ──────────────────────────────────


class TestExtractTechnologiesFromText:
    def test_finds_python(self) -> None:
        text = "We are looking for a Python developer with Django experience"
        result = extract_technologies_from_text(text)
        assert "python" in result

    def test_finds_multiple(self) -> None:
        text = "React frontend with Python backend, using PostgreSQL and Docker"
        result = extract_technologies_from_text(text)
        assert "python" in result
        assert "react" in result
        assert "postgresql" in result

    def test_word_boundary_avoids_false_positives(self) -> None:
        text = "JavaScript and Java are both used here"
        result = extract_technologies_from_text(text)
        assert "java" in result
        assert "javascript" in result

    def test_none_returns_empty(self) -> None:
        result = extract_technologies_from_text(None)
        assert result == set()

    def test_empty_string_returns_empty(self) -> None:
        result = extract_technologies_from_text("")
        assert result == set()


# ── Tests: extract_seniority_from_text ─────────────────────────────────────


class TestExtractSeniorityFromText:
    def test_finds_senior(self) -> None:
        text = "We are looking for a senior Python developer"
        assert extract_seniority_from_text(text) == "senior"

    def test_finds_junior(self) -> None:
        text = "Junior developer position, entry level"
        assert extract_seniority_from_text(text) == "junior"

    def test_finds_lead(self) -> None:
        text = "Tech lead position, staff engineer"
        assert extract_seniority_from_text(text) == "lead"

    def test_priority_lead_over_senior(self) -> None:
        text = "Senior tech lead position"
        assert extract_seniority_from_text(text) == "lead"

    def test_none_returns_none(self) -> None:
        assert extract_seniority_from_text(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert extract_seniority_from_text("") is None

    def test_no_match_returns_none(self) -> None:
        text = "We are looking for a developer"
        assert extract_seniority_from_text(text) is None