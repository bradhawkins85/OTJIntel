"""Regression tests for removal of the obsolete BCP incident table."""

from pathlib import Path


MIGRATION_PATH = Path(__file__).parent.parent / "migrations" / "001_init.sql"


def test_initial_migration_does_not_reference_removed_bcp_incident_table() -> None:
    """MySQL must not reject startup because an FK target no longer exists."""
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "REFERENCES bcp_incident" not in migration_sql
