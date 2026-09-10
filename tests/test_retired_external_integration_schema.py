from pathlib import Path


def test_consolidated_migration_excludes_retired_external_integration_table() -> None:
    migration_sql = (
        Path(__file__).parent.parent / "migrations" / "001_init.sql"
    ).read_text()
    retired_table = "external" + "_api_settings"

    assert retired_table not in migration_sql
