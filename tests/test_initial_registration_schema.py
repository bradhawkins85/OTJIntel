from pathlib import Path
import re


ROOT = Path(__file__).parent.parent
INIT_MIGRATION = ROOT / "migrations" / "001_init.sql"
UPGRADE_MIGRATION = ROOT / "migrations" / "003_allow_companyless_initial_admin.sql"


def _table_definition(sql: str, table: str) -> str:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS {table} \((.*?)\)\s*ENGINE=",
        sql,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def test_fresh_schema_allows_a_companyless_initial_administrator():
    users = _table_definition(INIT_MIGRATION.read_text(encoding="utf-8"), "users")

    assert re.search(r"\bcompany_id\s+INT\s+NULL\b", users)


def test_fresh_schema_contains_every_column_written_when_a_session_is_created():
    sessions = _table_definition(
        INIT_MIGRATION.read_text(encoding="utf-8"), "user_sessions"
    )

    for column in (
        "active_company_id",
        "impersonator_user_id",
        "impersonator_session_id",
        "impersonation_started_at",
    ):
        assert re.search(rf"\b{column}\b", sessions)


def test_upgrade_repairs_existing_registration_and_session_schema():
    migration = UPGRADE_MIGRATION.read_text(encoding="utf-8")

    assert re.search(r"MODIFY COLUMN company_id INT NULL", migration)
    for column in (
        "active_company_id",
        "impersonator_user_id",
        "impersonator_session_id",
        "impersonation_started_at",
    ):
        assert re.search(rf"ADD COLUMN IF NOT EXISTS {column}\b", migration)
