"""Persistence and validation for AI tag synonym groups."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.database import db

MAX_GROUPS = 200
MAX_TERMS_PER_GROUP = 20
MAX_TERM_LENGTH = 80


class InvalidSynonymGroup(ValueError):
    """Raised when a synonym group is not safe to store."""


def normalise_term(term: Any) -> str:
    return " ".join(str(term or "").strip().lower().replace("_", " ").replace("-", " ").split())


def validate_terms(terms: Any) -> list[str]:
    if not isinstance(terms, list):
        raise InvalidSynonymGroup("Terms must be a list")
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        text = normalise_term(term)
        if not text:
            continue
        if len(text) > MAX_TERM_LENGTH:
            raise InvalidSynonymGroup(f"Term '{text[:30]}…' is too long")
        if text not in seen:
            cleaned.append(text)
            seen.add(text)
    if len(cleaned) < 2:
        raise InvalidSynonymGroup("At least two unique terms are required")
    if len(cleaned) > MAX_TERMS_PER_GROUP:
        raise InvalidSynonymGroup(f"A synonym group can contain at most {MAX_TERMS_PER_GROUP} terms")
    return cleaned


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_terms = row.get("terms")
    if isinstance(raw_terms, list):
        terms = raw_terms
    else:
        try:
            decoded = json.loads(str(raw_terms or "[]"))
            terms = decoded if isinstance(decoded, list) else []
        except (TypeError, json.JSONDecodeError):
            terms = []
    row["terms"] = [str(term) for term in terms]
    return row


async def list_groups() -> list[dict[str, Any]]:
    rows = await db.fetch_all(
        "SELECT id, terms, created_at, updated_at FROM ai_tag_synonym_groups ORDER BY id ASC"
    )
    return [_decode_row(dict(row)) for row in rows]


async def get_group(group_id: int) -> dict[str, Any] | None:
    row = await db.fetch_one(
        "SELECT id, terms, created_at, updated_at FROM ai_tag_synonym_groups WHERE id = %s",
        (group_id,),
    )
    return _decode_row(dict(row)) if row else None


async def create_group(terms: list[Any]) -> dict[str, Any]:
    cleaned = validate_terms(terms)
    count = await db.fetch_one("SELECT COUNT(*) AS count FROM ai_tag_synonym_groups")
    if int((count or {}).get("count") or 0) >= MAX_GROUPS:
        raise InvalidSynonymGroup(f"At most {MAX_GROUPS} synonym groups are allowed")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    group_id = await db.execute_returning_lastrowid(
        "INSERT INTO ai_tag_synonym_groups (terms, created_at, updated_at) VALUES (%s, %s, %s)",
        (json.dumps(cleaned, separators=(",", ":")), now, now),
    )
    return await get_group(group_id) or {
        "id": group_id, "terms": cleaned, "created_at": now, "updated_at": now
    }


async def update_group(group_id: int, terms: list[Any]) -> dict[str, Any] | None:
    cleaned = validate_terms(terms)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    changed = await db.execute_rowcount(
        "UPDATE ai_tag_synonym_groups SET terms = %s, updated_at = %s WHERE id = %s",
        (json.dumps(cleaned, separators=(",", ":")), now, group_id),
    )
    return await get_group(group_id) if changed > 0 else None


async def delete_group(group_id: int) -> bool:
    return await db.execute_rowcount(
        "DELETE FROM ai_tag_synonym_groups WHERE id = %s", (group_id,)
    ) > 0
