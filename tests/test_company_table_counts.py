from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.repositories import scheduled_tasks


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_scheduled_task_counts_are_grouped_by_company(monkeypatch):
    fetch_all = AsyncMock(
        return_value=[
            {"company_id": 2, "task_count": 3},
            {"company_id": 7, "task_count": 1},
        ]
    )
    monkeypatch.setattr(scheduled_tasks.db, "fetch_all", fetch_all)

    result = await scheduled_tasks.count_tasks_by_company_ids([7, 2, 7])

    assert result == {2: 3, 7: 1}
    query, params = fetch_all.await_args.args
    assert "GROUP BY company_id" in query
    assert params == (2, 7)


def test_company_table_exposes_automation_counts_and_edit_links():
    template = open("app/templates/admin/companies.html", encoding="utf-8").read()

    assert '"key": "automations"' in template
    assert "recurring_invoice_items" not in template
    assert '"default_visible": false' in template
    assert 'data-column-key="automations"' in template
    assert (
        '<a href="/admin/companies/{{ company.id }}/edit">{{ company.name }}</a>'
        in template
    )


def test_company_admin_has_no_recurring_invoice_item_dependencies():
    handler = Path("app/features/companies/handlers.py").read_text(encoding="utf-8")
    edit_template = Path("app/templates/admin/company_edit.html").read_text(encoding="utf-8")
    admin_script = Path("app/static/js/admin.js").read_text(encoding="utf-8")

    assert "company_recurring_invoice_items" not in handler
    assert "recurring_invoice_items" not in handler
    assert "recurring-invoice-items" not in edit_template
    assert "recurring-item" not in admin_script
