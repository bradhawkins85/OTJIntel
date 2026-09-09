"""Regression tests for features intentionally excluded from OTJIntel."""

from pathlib import Path


def test_application_imports_without_removed_myportal_modules() -> None:
    from app.main import app

    assert app.title == "MyPortal"


def test_tray_integration_is_not_registered() -> None:
    from app.main import app

    routes = {(route.path, tuple(getattr(route, "methods", None) or ())) for route in app.routes}

    assert all("tray" not in path.lower() for path, _methods in routes)
    assert not Path("app/repositories/tray.py").exists()
    assert not Path("app/services/tray.py").exists()
