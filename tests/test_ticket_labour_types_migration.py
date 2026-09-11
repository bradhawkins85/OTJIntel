"""Regression tests for the ticket labour types migration."""

from pathlib import Path
import re


MIGRATION_PATH = Path(__file__).parent.parent / "migrations" / "001_init.sql"


def _ticket_labour_types_statement() -> str:
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS ticket_labour_types\s*\(.*?\)\s*"
        r"ENGINE=InnoDB[^;]*;",
        migration_sql,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group(0)


def test_ticket_labour_types_uses_valid_mysql_timestamp_defaults() -> None:
    statement = _ticket_labour_types_statement()

    assert statement.count("DEFAULT CURRENT_TIMESTAMP(6)") == 2
    assert "DEFAULT UTC_TIMESTAMP" not in statement


def test_ticket_labour_types_creation_is_idempotent() -> None:
    statement = _ticket_labour_types_statement()

    assert statement.startswith("CREATE TABLE IF NOT EXISTS ticket_labour_types")


def test_consolidated_migration_includes_default_labour_type_schema() -> None:
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    assert (
        "ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NOT NULL DEFAULT 0"
        in migration_sql
    )
    assert "idx_ticket_labour_types_default" in migration_sql


def test_upgrade_migration_repairs_default_labour_type_schema() -> None:
    migration_sql = (
        Path(__file__).parent.parent
        / "migrations"
        / "008_restore_ticket_labour_type_default.sql"
    ).read_text(encoding="utf-8")

    assert (
        "ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NOT NULL DEFAULT 0"
        in migration_sql
    )
    assert (
        "CREATE INDEX IF NOT EXISTS idx_ticket_labour_types_default"
        in migration_sql
    )
    assert "AND NOT EXISTS" in migration_sql
    assert "WHERE is_default = 1" in migration_sql
