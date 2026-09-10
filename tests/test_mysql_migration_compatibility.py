from __future__ import annotations

import pytest

from app.core.database import Database


class _Cursor:
    def __init__(self, existing_columns: set[str]) -> None:
        self.existing_columns = existing_columns
        self.executed: list[tuple[str, tuple[str, ...] | None]] = []
        self._found: tuple[str] | None = None

    async def execute(self, sql: str, params: tuple[str, ...] | None = None) -> None:
        self.executed.append((sql, params))
        if sql.startswith(("SHOW COLUMNS", "SHOW INDEX")):
            assert params is not None
            self._found = (params[0],) if params[0] in self.existing_columns else None

    async def fetchone(self) -> tuple[str] | None:
        return self._found


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mysql_conditional_add_skips_existing_and_adds_missing_column() -> None:
    cursor = _Cursor({"can_manage_assets"})
    statement = """ALTER TABLE user_companies
        ADD COLUMN IF NOT EXISTS can_manage_assets TINYINT(1),
        ADD COLUMN IF NOT EXISTS can_manage_invoices TINYINT(1) DEFAULT 0"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed == [
        (
            "SHOW COLUMNS FROM user_companies WHERE Field = %s",
            ("can_manage_assets",),
        ),
        (
            "SHOW COLUMNS FROM user_companies WHERE Field = %s",
            ("can_manage_invoices",),
        ),
        (
            "ALTER TABLE user_companies ADD COLUMN can_manage_invoices "
            "TINYINT(1) DEFAULT 0",
            None,
        ),
    ]


@pytest.mark.anyio
async def test_mysql_conditional_add_preserves_commas_inside_column_type() -> None:
    cursor = _Cursor(set())
    statement = """ALTER TABLE apps ADD COLUMN IF NOT EXISTS billing_cycle
        ENUM('monthly','annual') NOT NULL DEFAULT 'monthly'"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed[-1] == (
        "ALTER TABLE apps ADD COLUMN billing_cycle "
        "ENUM('monthly','annual') NOT NULL DEFAULT 'monthly'",
        None,
    )


@pytest.mark.anyio
async def test_mysql_conditional_add_supports_indexes_mixed_with_columns() -> None:
    cursor = _Cursor({"m365_message_id"})
    statement = """ALTER TABLE ticket_replies
        ADD COLUMN IF NOT EXISTS m365_message_id VARCHAR(512) NULL,
        ADD INDEX IF NOT EXISTS idx_m365_message (m365_message_id(191))"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed[-1] == (
        "ALTER TABLE ticket_replies ADD INDEX idx_m365_message "
        "(m365_message_id(191))",
        None,
    )


@pytest.mark.anyio
async def test_regular_mysql_statement_executes_unchanged() -> None:
    cursor = _Cursor(set())

    await Database()._execute_mysql_migration_statement(
        cursor, "ALTER TABLE users MODIFY email VARCHAR(255) NOT NULL"
    )

    assert cursor.executed == [
        ("ALTER TABLE users MODIFY email VARCHAR(255) NOT NULL", None)
    ]
