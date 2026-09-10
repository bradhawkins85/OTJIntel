from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.repositories import scheduled_tasks as scheduled_tasks_repo


@pytest.mark.anyio
async def test_ensure_system_update_task_creates_hourly_global_task(monkeypatch):
    monkeypatch.setattr(
        scheduled_tasks_repo.db, "fetch_one", AsyncMock(return_value=None)
    )
    create_task = AsyncMock(return_value={"id": 7, "command": "system_update"})
    monkeypatch.setattr(scheduled_tasks_repo, "create_task", create_task)

    task = await scheduled_tasks_repo.ensure_system_update_task()

    assert task == {"id": 7, "command": "system_update"}
    create_task.assert_awaited_once_with(
        name="Update MyPortal system",
        command="system_update",
        cron="0 * * * *",
        description="Check GitHub hourly and schedule available system updates.",
        active=True,
        exclude_from_calendar=True,
    )


@pytest.mark.anyio
async def test_ensure_system_update_task_preserves_inactive_task(monkeypatch):
    existing = {
        "id": 8,
        "company_id": None,
        "name": "Updates disabled by administrator",
        "command": "system_update",
        "cron": "0 * * * *",
        "active": 0,
        "exclude_from_calendar": 1,
    }
    monkeypatch.setattr(
        scheduled_tasks_repo.db, "fetch_one", AsyncMock(return_value=existing)
    )
    create_task = AsyncMock()
    monkeypatch.setattr(scheduled_tasks_repo, "create_task", create_task)

    task = await scheduled_tasks_repo.ensure_system_update_task()

    assert task["id"] == 8
    assert task["active"] is False
    create_task.assert_not_awaited()
