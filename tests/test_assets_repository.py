import asyncio
from datetime import datetime, timezone

from app.repositories import assets as assets_repo


def test_list_company_assets_does_not_select_retired_syncro_id(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_fetch_all(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr(assets_repo.db, "fetch_all", fake_fetch_all)

    assert asyncio.run(assets_repo.list_company_assets(12)) == []
    assert "syncro_asset_id" not in captured["sql"]
    assert captured["params"] == (12,)


def test_upsert_asset_does_not_write_retired_syncro_id(monkeypatch):
    statements: list[str] = []

    async def fake_fetch_one(sql, params=None):
        statements.append(sql)
        return None

    async def fake_insert(sql, params=None):
        statements.append(sql)
        return 42

    monkeypatch.setattr(assets_repo.db, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(assets_repo.db, "execute_returning_lastrowid", fake_insert)

    result = asyncio.run(
        assets_repo.upsert_asset(company_id=12, name="Workstation", match_name=True)
    )

    assert result == 42
    assert all("syncro_asset_id" not in statement for statement in statements)


def test_count_active_assets_builds_expected_query(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_fetch_one(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return {"total": 7}

    monkeypatch.setattr(assets_repo.db, "fetch_one", fake_fetch_one)

    since = datetime(2024, 4, 20, 15, 30, tzinfo=timezone.utc)
    result = asyncio.run(assets_repo.count_active_assets(company_id="5", since=since))

    assert result == 7
    assert "company_id = %s" in captured["sql"]
    assert "last_sync >= %s" in captured["sql"]
    assert captured["params"] == (5, "2024-04-20 15:30:00")


def test_count_active_assets_handles_empty_results(monkeypatch):
    async def fake_fetch_one(sql, params=None):
        return None

    monkeypatch.setattr(assets_repo.db, "fetch_one", fake_fetch_one)

    result = asyncio.run(assets_repo.count_active_assets())

    assert result == 0
