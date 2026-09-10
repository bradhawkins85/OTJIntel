from pathlib import Path


def test_click_to_call_frontend_is_not_loaded_or_requested():
    frontend_files = (
        Path("app/templates/base.html"),
        Path("app/templates/admin/profile.html"),
        Path("app/static/js/profile.js"),
        Path("app/static/js/ticket_detail.js"),
    )

    for path in frontend_files:
        content = path.read_text(encoding="utf-8").lower()
        assert "click-to-call" not in content
        assert "/api/click-to-call" not in content

    assert not Path("app/static/js/click_to_call.js").exists()
