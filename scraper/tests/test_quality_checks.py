"""Tests for data quality checks."""

from __future__ import annotations

from unittest.mock import patch

from scraper.quality.checks import (
    _check_volume,
    _check_empty_descriptions,
    _check_sources_with_data,
    _check_tech_coverage,
    run_checks,
)


class TestCheckVolume:
    """Tests for _check_volume."""

    def test_no_history_returns_false(self) -> None:
        """When avg_7d is 0, no comparison can be made, check passes."""
        assert _check_volume(5, 0) is False

    def test_sufficient_volume_passes(self) -> None:
        """100 today vs 150 average → 100 > 75 (50% of 150), check passes."""
        assert _check_volume(100, 150) is False

    def test_low_volume_fails(self) -> None:
        """30 today vs 200 average → 30 < 100 (50% of 200), check fails."""
        result = _check_volume(30, 200)
        assert result is True

    def test_exact_threshold_passes(self) -> None:
        """Exactly at 50% threshold does NOT fail (not strictly less)."""
        assert _check_volume(75, 150) is False

    def test_just_below_threshold_fails(self) -> None:
        """Just below 50% threshold fails."""
        assert _check_volume(74, 150) is True


class TestCheckEmptyDescriptions:
    """Tests for _check_empty_descriptions."""

    def test_few_empty_passes(self) -> None:
        """2 empty out of 10 → 20% < 30%, check passes."""
        assert _check_empty_descriptions(2, 10) is False

    def test_many_empty_fails(self) -> None:
        """4 empty out of 10 → 40% > 30%, check fails."""
        result = _check_empty_descriptions(4, 10)
        assert result is True

    def test_zero_total_passes(self) -> None:
        """No jobs at all → cannot evaluate, check passes."""
        assert _check_empty_descriptions(0, 0) is False

    def test_exact_threshold_passes(self) -> None:
        """Exactly 30% does NOT fail (must exceed, not equal)."""
        assert _check_empty_descriptions(3, 10) is False

    def test_just_above_threshold_fails(self) -> None:
        """Just above 30% fails."""
        assert _check_empty_descriptions(4, 10) is True


class TestCheckSourcesWithData:
    """Tests for _check_sources_with_data."""

    def test_all_sources_have_data_passes(self) -> None:
        """All sources reported data, check passes."""
        assert (
            _check_sources_with_data(
                ["getonboard", "remotive"],
                ["getonboard", "remotive"],
            )
            is False
        )

    def test_missing_source_fails(self) -> None:
        """One source has no data, check fails."""
        result = _check_sources_with_data(
            ["getonboard"],
            ["getonboard", "remotive"],
        )
        assert result is True

    def test_extra_source_with_data_is_fine(self) -> None:
        """Sources with data not in all_sources is OK (extra data)."""
        assert (
            _check_sources_with_data(
                ["getonboard", "remotive", "linkedin"],
                ["getonboard", "remotive"],
            )
            is False
        )

    def test_empty_all_sources_passes(self) -> None:
        """No active sources to check → trivially passes."""
        assert _check_sources_with_data(["getonboard"], []) is False


class TestCheckTechCoverage:
    """Tests for _check_tech_coverage."""

    def test_good_coverage_passes(self) -> None:
        """3 without tech out of 10 → 30% < 60%, check passes."""
        assert _check_tech_coverage(3, 10) is False

    def test_poor_coverage_fails(self) -> None:
        """7 without tech out of 10 → 70% > 60%, check fails."""
        result = _check_tech_coverage(7, 10)
        assert result is True

    def test_zero_total_passes(self) -> None:
        """No jobs → cannot evaluate, check passes."""
        assert _check_tech_coverage(0, 0) is False

    def test_exact_threshold_passes(self) -> None:
        """Exactly 60% does NOT fail (must exceed, not equal)."""
        assert _check_tech_coverage(6, 10) is False


class TestRunChecks:
    """Tests for run_checks (integration of all checks + alert)."""

    @patch("scraper.quality.checks.send_alert")
    def test_all_pass_no_alert(self, mock_alert: object) -> None:
        """When all checks pass, no alert is sent."""
        result = run_checks(
            jobs_today=100,
            avg_7d=150,
            empty_descriptions=2,
            total=10,
            sources_with_data=["getonboard"],
            all_sources=["getonboard"],
            jobs_without_tech=3,
        )
        assert result["checks_passed"] is True
        assert result["failed_checks"] == []
        assert mock_alert.call_count == 0  # type: ignore[attr-defined]

    @patch("scraper.quality.checks.send_alert")
    def test_all_fail_sends_consolidated_alert(self, mock_alert: object) -> None:
        """When all 4 checks fail, one consolidated alert is sent."""
        result = run_checks(
            jobs_today=30,
            avg_7d=200,  # volume too low
            empty_descriptions=4,
            total=10,  # 40% > 30%
            sources_with_data=["getonboard"],
            all_sources=["getonboard", "remotive"],  # remotive missing
            jobs_without_tech=7,  # 70% > 60%
        )
        assert result["checks_passed"] is False
        assert len(result["failed_checks"]) == 4
        assert mock_alert.call_count == 1  # type: ignore[attr-defined]
        alert_message = mock_alert.call_args[0][0]  # type: ignore[attr-defined]
        assert "Volumen bajo" in alert_message
        assert "Descripciones vacías" in alert_message
        assert "remotive" in alert_message
        assert "Tecnologías no detectadas" in alert_message

    @patch("scraper.quality.checks.send_alert")
    def test_volume_only_fail_sends_alert(self, mock_alert: object) -> None:
        """When only volume check fails, alert includes only that."""
        result = run_checks(
            jobs_today=30,
            avg_7d=200,
            empty_descriptions=1,
            total=10,
            sources_with_data=["getonboard"],
            all_sources=["getonboard"],
            jobs_without_tech=2,
        )
        assert result["checks_passed"] is False
        assert result["failed_checks"] == ["volumen_bajo"]
        assert mock_alert.call_count == 1  # type: ignore[attr-defined]

    @patch("scraper.quality.checks.send_alert")
    def test_default_all_sources_equals_sources_with_data(
        self, mock_alert: object
    ) -> None:
        """When all_sources is not provided, defaults to sources_with_data."""
        result = run_checks(
            jobs_today=100,
            avg_7d=150,
            empty_descriptions=1,
            total=10,
            sources_with_data=["getonboard"],
            # all_sources not provided → defaults to same as sources_with_data
            jobs_without_tech=2,
        )
        assert result["checks_passed"] is True
        assert mock_alert.call_count == 0  # type: ignore[attr-defined]

    @patch("scraper.quality.checks.send_alert")
    def test_default_jobs_without_tech_is_zero(
        self, mock_alert: object
    ) -> None:
        """When jobs_without_tech is not provided, defaults to 0."""
        result = run_checks(
            jobs_today=100,
            avg_7d=150,
            empty_descriptions=1,
            total=10,
            sources_with_data=["getonboard"],
        )
        assert result["checks_passed"] is True