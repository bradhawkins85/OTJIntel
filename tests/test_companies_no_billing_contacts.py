"""Regression coverage for the removal of company billing contacts."""

from pathlib import Path

from app.features.companies import admin_routes


def test_company_routes_do_not_expose_billing_contacts() -> None:
    paths = {route.path for route in admin_routes.router.routes}

    assert not any("billing-contacts" in path for path in paths)


def test_company_edit_does_not_depend_on_billing_contacts_table() -> None:
    handlers = Path("app/features/companies/handlers.py").read_text()
    template = Path("app/templates/admin/company_edit.html").read_text()

    assert "billing_contacts" not in handlers
    assert "billing-contact" not in template

