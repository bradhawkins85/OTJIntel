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
