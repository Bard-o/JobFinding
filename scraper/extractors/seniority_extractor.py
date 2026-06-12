"""Extrae seniority desde jobs.description usando keywords definidas en ARCHITECTURE.md."""

from __future__ import annotations

import re
from typing import Optional

# Keywords por nivel, evaluadas en orden de prioridad (lead > senior > mid > junior)
SENIORITY_KEYWORDS: dict[str, list[str]] = {
    "lead": ["lead", "staff", "principal", "head of", "tech lead"],
    "senior": ["senior", "sr.", "sr "],
    "mid": ["mid", "middle", "semi-senior", "ssr", "semi senior"],
    "junior": ["junior", "jr.", "jr ", "entry level", "entry-level", "trainee"],
}

# Orden de prioridad (primero encontrado gana)
SENIORITY_PRIORITY: list[str] = ["lead", "senior", "mid", "junior"]


def extract_seniority_from_text(description: str | None) -> Optional[str]:
    """Extrae seniority desde un texto usando keywords.

    Evalúa en orden de prioridad: lead > senior > mid > junior.
    Si no hay match, retorna None.

    Args:
        description: Texto de la descripción del job (puede ser None)

    Returns:
        "lead", "senior", "mid", "junior" o None
    """
    if not description:
        return None

    text_lower = description.lower()

    for level in SENIORITY_PRIORITY:
        keywords = SENIORITY_KEYWORDS[level]
        for keyword in keywords:
            # Usar word boundary para evitar falsos positivos
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                return level

    return None


def update_job_seniority(
    job_id: int, description: str | None, engine
) -> bool:
    """Extrae seniority de la descripción y actualiza el campo seniority del job.

    Args:
        job_id: ID del job en la DB
        description: Texto de la descripción (puede ser None)
        engine: SQLAlchemy engine

    Returns:
        True si se actualizó, False si no hubo cambio
    """
    from sqlalchemy import text

    seniority = extract_seniority_from_text(description)

    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE jobs SET seniority = :seniority WHERE id = :job_id"),
            {"seniority": seniority, "job_id": job_id},
        )
        return result.rowcount > 0