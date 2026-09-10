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
