"""Data quality checks — detect anomalies in scraper data.

The 4 checks defined in ARCHITECTURE.md:
- Volume: jobs today < 50% of 7-day daily average
- Empty descriptions: >30% with description < 50 characters
- Source with no data: any active source with 0 new jobs today
- Tech coverage: >60% of jobs without any linked technology

If any check fails → send Telegram alert and continue (fail silently).
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

import structlog

from scraper.alerts.telegram import send_alert

logger = structlog.get_logger(__name__)

# Configurable thresholds
VOLUME_THRESHOLD = 0.5  # 50% of 7-day average
EMPTY_DESC_THRESHOLD = 0.3  # 30%
NO_TECH_THRESHOLD = 0.6  # 60%


def _check_volume(jobs_today: int, avg_7d: float) -> bool:
    """Check: daily job volume vs 7-day average.

    Args:
        jobs_today: Number of new jobs inserted today.
        avg_7d: Average daily job count over the last 7 days.

    Returns:
        True if the check FAILS (volume too low), False if it passes.
    """
    if avg_7d <= 0:
        # No history to compare against — cannot evaluate
        return False

    return jobs_today < avg_7d * VOLUME_THRESHOLD


def _check_empty_descriptions(empty_count: int, total: int) -> bool:
    """Check: percentage of jobs with empty or very short descriptions.

    Args:
        empty_count: Number of jobs with description < 50 characters.
        total: Total number of jobs processed.

    Returns:
        True if the check FAILS (too many empty descriptions), False if it passes.
    """
    if total == 0:
        return False

    return (empty_count / total) > EMPTY_DESC_THRESHOLD


def _check_sources_with_data(
    sources_with_data: List[str],
    all_sources: List[str],
) -> bool:
    """Check: all active sources have new data.

    Args:
        sources_with_data: Source names that had new jobs today.
        all_sources: All active source names.

    Returns:
        True if any source has no data, False if all sources have data.
    """
    return any(s not in sources_with_data for s in all_sources)


def _check_tech_coverage(jobs_without_tech: int, total: int) -> bool:
    """Check: percentage of jobs without any linked technology.

    Args:
        jobs_without_tech: Number of jobs with no technology links.
        total: Total number of jobs.

    Returns:
        True if too many jobs lack technology, False if coverage is acceptable.
    """
    if total == 0:
        return False

    return (jobs_without_tech / total) > NO_TECH_THRESHOLD


def run_checks(
    jobs_today: int,
    avg_7d: float,
    empty_descriptions: int,
    total: int,
    sources_with_data: List[str],
    all_sources: Optional[List[str]] = None,
    jobs_without_tech: Optional[int] = None,
) -> dict:
    """Run the 4 data quality checks and send an alert if any fail.

    Args:
        jobs_today: Number of new jobs inserted today.
        avg_7d: Average daily job count over the last 7 days.
        empty_descriptions: Jobs with description < 50 characters.
        total: Total number of jobs processed today.
        sources_with_data: Source names that had new jobs today.
        all_sources: All active source names (default: same as sources_with_data).
        jobs_without_tech: Jobs without any linked technology (default: 0).

    Returns:
        Dict with checks_passed (bool) and failed_checks (list of strings).
    """
    if all_sources is None:
        all_sources = sources_with_data

    if jobs_without_tech is None:
        jobs_without_tech = 0

    failed_checks: list[str] = []

    # Check 1: Volume
    if _check_volume(jobs_today, avg_7d):
        failed_checks.append("volumen_bajo")

    # Check 2: Empty descriptions
    if _check_empty_descriptions(empty_descriptions, total):
        failed_checks.append("descripciones_vacias")

    # Check 3: Sources with no data
    if _check_sources_with_data(sources_with_data, all_sources):
        failed_checks.append("fuente_sin_datos")

    # Check 4: Tech coverage
    if _check_tech_coverage(jobs_without_tech, total):
        failed_checks.append("tecnologias_no_detectadas")

    # If any checks failed, send consolidated alert
    if failed_checks:
        today = date.today().isoformat()
        alert_lines = [
            f"⚠️ JobFinding — Data Quality Alert\nFecha: {today}\nChecks fallidos:"
        ]

        for check in failed_checks:
            if check == "volumen_bajo":
                threshold = avg_7d * VOLUME_THRESHOLD
                alert_lines.append(
                    f"- Volumen bajo: {jobs_today} ofertas "
                    f"(umbral: {threshold:.0f}, promedio 7d: {avg_7d:.0f})"
                )
            elif check == "descripciones_vacias":
                ratio = (empty_descriptions / total * 100) if total > 0 else 0
                alert_lines.append(
                    f"- Descripciones vacías: {ratio:.1f}% "
                    f"({empty_descriptions}/{total})"
                )
            elif check == "fuente_sin_datos":
                sources_no_data = sorted(
                    s for s in all_sources if s not in sources_with_data
                )
                alert_lines.append(
                    f"- Fuente sin datos: {', '.join(sources_no_data)}"
                )
            elif check == "tecnologias_no_detectadas":
                ratio = (jobs_without_tech / total * 100) if total > 0 else 0
                alert_lines.append(
                    f"- Tecnologías no detectadas: {ratio:.1f}% "
                    f"({jobs_without_tech}/{total})"
                )

        full_message = "\n".join(alert_lines)
        send_alert(full_message)
        logger.warning("quality_checks_failed", failed_checks=failed_checks)
    else:
        logger.info("quality_checks_passed", jobs_today=jobs_today)

    return {
        "checks_passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
    }