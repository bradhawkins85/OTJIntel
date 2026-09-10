from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.database import Database


class _Cursor:
    def __init__(
        self,
        existing_columns: set[str],
        existing_constraints: set[str] | None = None,
    ) -> None:
        self.existing_columns = existing_columns
        self.existing_constraints = existing_constraints or set()
        self.executed: list[tuple[str, tuple[str, ...] | None]] = []
        self._found: tuple[str] | None = None

    async def execute(self, sql: str, params: tuple[str, ...] | None = None) -> None:
        self.executed.append((sql, params))
        if sql.startswith(("SHOW COLUMNS", "SHOW INDEX")):
            assert params is not None
            self._found = (params[0],) if params[0] in self.existing_columns else None
        elif sql.startswith("SELECT CONSTRAINT_NAME FROM information_schema"):
            assert params is not None
            self._found = (
                (params[1],) if params[1] in self.existing_constraints else None
            )

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
async def test_mysql_conditional_drop_removes_only_existing_columns() -> None:
    cursor = _Cursor({"default_price"})
    statement = """ALTER TABLE apps
        DROP COLUMN IF EXISTS default_price,
        DROP COLUMN IF EXISTS contract_term"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed == [
        ("SHOW COLUMNS FROM apps WHERE Field = %s", ("default_price",)),
        ("ALTER TABLE apps DROP COLUMN default_price", None),
        ("SHOW COLUMNS FROM apps WHERE Field = %s", ("contract_term",)),
    ]


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
async def test_asset_detail_migration_skips_columns_already_present() -> None:
    cursor = _Cursor({"os_name", "cpu_name"})
    statement = """ALTER TABLE assets
        ADD COLUMN IF NOT EXISTS os_name VARCHAR(255) DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS cpu_name VARCHAR(255) DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS ram_gb INT DEFAULT NULL"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    alterations = [sql for sql, _ in cursor.executed if sql.startswith("ALTER TABLE")]
    assert alterations == [
        "ALTER TABLE assets ADD COLUMN ram_gb INT DEFAULT NULL"
    ]


@pytest.mark.anyio
async def test_mysql_add_index_skips_existing_index_in_mixed_alter() -> None:
    cursor = _Cursor({"company_id", "idx_audit_logs_company_id"})
    statement = """ALTER TABLE audit_logs
        ADD COLUMN IF NOT EXISTS company_id INT NULL AFTER user_id,
        ADD INDEX idx_audit_logs_company_id (company_id)"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed == [
        ("SHOW COLUMNS FROM audit_logs WHERE Field = %s", ("company_id",)),
        (
            "SHOW INDEX FROM audit_logs WHERE Key_name = %s",
            ("idx_audit_logs_company_id",),
        ),
    ]


@pytest.mark.anyio
async def test_mysql_add_unique_key_preserves_unique_when_missing() -> None:
    cursor = _Cursor(set())

    await Database()._execute_mysql_migration_statement(
        cursor,
        "ALTER TABLE assets ADD UNIQUE KEY assets_company_tactical_id "
        "(company_id, tactical_asset_id)",
    )

    assert cursor.executed == [
        (
            "SHOW INDEX FROM assets WHERE Key_name = %s",
            ("assets_company_tactical_id",),
        ),
        (
            "ALTER TABLE assets ADD UNIQUE KEY assets_company_tactical_id "
            "(company_id, tactical_asset_id)",
            None,
        ),
    ]


@pytest.mark.anyio
async def test_mysql_create_index_skips_existing_index() -> None:
    cursor = _Cursor({"idx_audit_logs_entity"})

    await Database()._execute_mysql_migration_statement(
        cursor,
        "CREATE INDEX idx_audit_logs_entity "
        "ON audit_logs(entity_type, entity_id)",
    )

    assert cursor.executed == [
        (
            "SHOW INDEX FROM audit_logs WHERE Key_name = %s",
            ("idx_audit_logs_entity",),
        ),
    ]


@pytest.mark.anyio
async def test_mysql_create_unique_index_adds_missing_index() -> None:
    cursor = _Cursor(set())

    await Database()._execute_mysql_migration_statement(
        cursor,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    )

    assert cursor.executed == [
        ("SHOW INDEX FROM users WHERE Key_name = %s", ("idx_users_email",)),
        ("CREATE UNIQUE INDEX idx_users_email ON users (email)", None),
    ]


@pytest.mark.anyio
async def test_mysql_conditional_drop_index_removes_existing_index() -> None:
    cursor = _Cursor({"uq_ticket_watchers_ticket_user"})

    await Database()._execute_mysql_migration_statement(
        cursor,
        "ALTER TABLE ticket_watchers "
        "DROP INDEX IF EXISTS uq_ticket_watchers_ticket_user",
    )

    assert cursor.executed == [
        (
            "SHOW INDEX FROM ticket_watchers WHERE Key_name = %s",
            ("uq_ticket_watchers_ticket_user",),
        ),
        (
            "ALTER TABLE ticket_watchers "
            "DROP INDEX uq_ticket_watchers_ticket_user",
            None,
        ),
    ]


@pytest.mark.anyio
async def test_mysql_conditional_drop_index_skips_missing_index() -> None:
    cursor = _Cursor(set())

    await Database()._execute_mysql_migration_statement(
        cursor,
        "ALTER TABLE ticket_watchers "
        "DROP INDEX IF EXISTS uq_ticket_watchers_ticket_user",
    )

    assert cursor.executed == [
        (
            "SHOW INDEX FROM ticket_watchers WHERE Key_name = %s",
            ("uq_ticket_watchers_ticket_user",),
        ),
    ]


@pytest.mark.anyio
async def test_mysql_conditional_add_supports_mixed_modify_clause() -> None:
    cursor = _Cursor(set())
    statement = """ALTER TABLE staff
        MODIFY date_onboarded DATETIME NULL,
        ADD COLUMN IF NOT EXISTS date_offboarded DATETIME NULL"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert cursor.executed == [
        ("ALTER TABLE staff MODIFY date_onboarded DATETIME NULL", None),
        ("SHOW COLUMNS FROM staff WHERE Field = %s", ("date_offboarded",)),
        ("ALTER TABLE staff ADD COLUMN date_offboarded DATETIME NULL", None),
    ]


def test_consolidated_migration_has_no_unconditional_add_column() -> None:
    migration = Path("migrations/001_init.sql").read_text(encoding="utf-8")

    assert re.search(
        r"\bADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS\b)",
        migration,
        flags=re.IGNORECASE,
    ) is None


def test_consolidated_migration_does_not_reference_removed_price_alert_table() -> None:
    migration = Path("migrations/001_init.sql").read_text(encoding="utf-8")

    assert "product_price_alerts" not in migration


def test_sqlite_adapter_places_autoincrement_after_primary_key() -> None:
    sql = Database()._adapt_sql_for_sqlite(
        "CREATE TABLE example (id INT AUTO_INCREMENT PRIMARY KEY)"
    )

    assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql


@pytest.mark.anyio
async def test_regular_mysql_statement_executes_unchanged() -> None:
    cursor = _Cursor(set())

    await Database()._execute_mysql_migration_statement(
        cursor, "ALTER TABLE users MODIFY email VARCHAR(255) NOT NULL"
    )

    assert cursor.executed == [
        ("ALTER TABLE users MODIFY email VARCHAR(255) NOT NULL", None)
    ]


@pytest.mark.anyio
async def test_mysql_missing_foreign_key_is_skipped_before_replacement() -> None:
    cursor = _Cursor(set())
    statement = """ALTER TABLE user_companies
        DROP FOREIGN KEY user_companies_ibfk_1,
        ADD CONSTRAINT fk_user_companies_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    alterations = [sql for sql, _ in cursor.executed if sql.startswith("ALTER TABLE")]
    assert alterations == [
        "ALTER TABLE user_companies ADD CONSTRAINT fk_user_companies_user "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    ]


@pytest.mark.anyio
async def test_mysql_foreign_key_replacement_is_idempotent() -> None:
    cursor = _Cursor(set(), {"fk_user_companies_user"})
    statement = """ALTER TABLE user_companies
        DROP FOREIGN KEY user_companies_ibfk_1,
        ADD CONSTRAINT fk_user_companies_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"""

    await Database()._execute_mysql_migration_statement(cursor, statement)

    assert not any(
        sql.startswith("ALTER TABLE") for sql, _ in cursor.executed
    )


@pytest.mark.anyio
async def test_mysql_existing_foreign_key_is_dropped() -> None:
    cursor = _Cursor(set(), {"user_companies_ibfk_1"})

    await Database()._execute_mysql_migration_statement(
        cursor,
        "ALTER TABLE user_companies DROP FOREIGN KEY user_companies_ibfk_1",
    )

    assert cursor.executed[-1] == (
        "ALTER TABLE user_companies DROP FOREIGN KEY user_companies_ibfk_1",
        None,
    )
