"""Regression coverage for manually creating assets."""

from pathlib import Path

from starlette.requests import Request
import pytest

from app.features.assets import routes as assets_routes
from app.schemas.assets import AssetCreate


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/assets", "headers": []})


@pytest.mark.anyio
async def test_create_asset_scopes_new_record_to_active_company(monkeypatch):
    user = {"id": 7, "company_id": 42, "is_super_admin": False}
    membership = {"menu_permissions": {"menu.assets": "write"}}

    async def fake_load_context(request):
        return user, membership, {"id": 42}, 42, None

    async def fake_create_asset(*, company_id, values):
        assert company_id == 42
        assert values["name"] == "Reception PC"
        assert values["ram_gb"] == 16
        assert "tactical_asset_id" not in values
        return 123

    async def fake_get_asset(asset_id):
        assert asset_id == 123
        return {"id": 123, "company_id": 42, "name": "Reception PC", "ram_gb": 16}

    monkeypatch.setattr(assets_routes, "_load_asset_context", fake_load_context)
    monkeypatch.setattr(assets_routes.asset_repo, "create_asset", fake_create_asset)
    monkeypatch.setattr(assets_routes.asset_repo, "get_asset_by_id", fake_get_asset)

    response = await assets_routes.create_asset(
        _request(), AssetCreate(name="Reception PC", ram_gb=16)
    )

    assert response["id"] == 123


@pytest.mark.anyio
async def test_create_asset_rejects_read_only_access(monkeypatch):
    user = {"id": 7, "company_id": 42, "is_super_admin": False}
    membership = {"menu_permissions": {"menu.assets": "read"}}

    async def fake_load_context(request):
        return user, membership, {"id": 42}, 42, None

    monkeypatch.setattr(assets_routes, "_load_asset_context", fake_load_context)

    with pytest.raises(assets_routes.HTTPException) as exc_info:
        await assets_routes.create_asset(_request(), AssetCreate(name="Reception PC"))

    assert exc_info.value.status_code == 403


def test_assets_action_menu_offers_creation_not_network_devices():
    template = (
        Path(__file__).parents[1] / "app" / "templates" / "assets" / "index.html"
    ).read_text()

    assert '"label": "Create Asset"' in template
    assert '"label": "Network devices"' not in template
