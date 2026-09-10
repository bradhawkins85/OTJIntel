from unittest.mock import AsyncMock

import pytest
from fastapi import Request

from app import main


def _request(path: str = "/register") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
        }
    )


@pytest.mark.anyio
async def test_public_context_always_disables_plausible_safely():
    context = await main._build_public_context(_request())

    assert context["plausible_config"] == {
        "enabled": False,
        "base_url": "",
        "site_domain": "",
        "track_pageviews": False,
    }


@pytest.mark.anyio
async def test_register_template_renders_with_public_context():
    request = _request()
    context = await main._build_public_context(
        request,
        extra={"title": "Create super administrator", "is_first_user": True},
    )

    response = main.templates.TemplateResponse(request, "auth/register.html", context)

    assert response.status_code == 200
    assert b"Create super administrator" in response.body


@pytest.mark.anyio
async def test_base_context_builds_enabled_plausible_config(monkeypatch):
    request = _request("/portal")
    request.state.available_companies = []
    request.state.module_lookup = {
        "plausible": {
            "enabled": True,
            "settings": {
                "base_url": "https://analytics.example.com/",
                "site_domain": "portal.example.com",
                "track_pageviews": False,
            },
        }
    }
    monkeypatch.setattr(main.session_manager, "load_session", AsyncMock(return_value=None))
    monkeypatch.setattr(main, "_is_helpdesk_technician", AsyncMock(return_value=False))
    monkeypatch.setattr(main, "_has_admin_technician_access", AsyncMock(return_value=False))
    monkeypatch.setattr(main, "_has_issue_tracker_access", AsyncMock(return_value=False))
    monkeypatch.setattr(main, "_has_marketing_access", AsyncMock(return_value=False))
    monkeypatch.setattr(main.notifications_repo, "count_notifications", AsyncMock(return_value=0))

    context = await main._build_base_context(
        request,
        {"id": 1, "email": "admin@example.com", "is_super_admin": True},
    )

    assert context["plausible_config"] == {
        "enabled": True,
        "base_url": "https://analytics.example.com",
        "site_domain": "portal.example.com",
        "track_pageviews": False,
    }


def test_plausible_config_rejects_credential_bearing_url():
    config = main._build_plausible_config(
        {
            "plausible": {
                "enabled": True,
                "settings": {
                    "base_url": "https://user:secret@analytics.example.com",
                    "site_domain": "portal.example.com",
                    "track_pageviews": True,
                },
            }
        },
        {"id": 1},
    )

    assert config["enabled"] is False
