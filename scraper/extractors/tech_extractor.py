"""Extrae tecnologías desde jobs.description usando regex word-boundary."""

from __future__ import annotations

import re
from typing import Set

import structlog

logger = structlog.get_logger(__name__)

# Cache del diccionario de tecnologías cargado desde la DB
_tech_cache: dict[str, int] = {}  # name_lower -> id
_cache_loaded = False


def load_technology_dict(engine) -> dict[str, int]:
    """Carga el diccionario de tecnologías desde la DB.

    Returns:
        dict mapping lowercase tech name -> technology id
    """
    global _tech_cache, _cache_loaded
    if _cache_loaded:
        return _tech_cache

    from sqlalchemy import text

    with engine.begin() as conn:
        result = conn.execute(text("SELECT id, name FROM technologies"))
        for row in result:
            _tech_cache[row[1].lower()] = row[0]

    _cache_loaded = True
    logger.info("tech_dict_loaded", count=len(_tech_cache))
    return _tech_cache


def extract_technologies_from_text(description: str | None) -> set[str]:
    """Extrae nombres de tecnologías desde un texto usando regex word-boundary.

    Usa \\b para evitar falsos positivos (ej. 'Java' dentro de 'JavaScript').
    Case-insensitive.

    Args:
        description: Texto de la descripción del job (puede ser None)

    Returns:
        Set de nombres de tecnologías en lowercase encontradas
    """
    if not description:
        return set()

    tech_dict = _tech_cache  # asume que está cargado
    found = set()

    for tech_name, tech_id in tech_dict.items():
        # Usar word boundaries para evitar falsos positivos
        pattern = rf"\b{re.escape(tech_name)}\b"
        if re.search(pattern, description, re.IGNORECASE):
            found.add(tech_name)

    return found


def link_technologies_from_description(
    job_id: int, description: str | None, engine
) -> int:
    """Hace matching de tecnologías en la descripción y las linkea a job_technologies.

    Args:
        job_id: ID del job en la DB
        description: Texto de la descripción (puede ser None)
        engine: SQLAlchemy engine

    Returns:
        Cantidad de links creados
    """
    from sqlalchemy import text

    found = extract_technologies_from_text(description)
    if not found:
        return 0

    links_created = 0
    with engine.begin() as conn:
        for tech_name in found:
            tech_id = _tech_cache.get(tech_name)
            if tech_id is None:
                continue

            result = conn.execute(
                text(
                    "INSERT INTO job_technologies (job_id, technology_id) "
                    "VALUES (:job_id, :tech_id) "
                    "ON CONFLICT (job_id, technology_id) DO NOTHING"
                ),
                {"job_id": job_id, "tech_id": tech_id},
            )
            if result.rowcount > 0:
                links_created += 1

    return links_created