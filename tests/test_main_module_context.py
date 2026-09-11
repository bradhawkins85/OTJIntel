"""Regression tests for integration modules in the shared page context."""

from app.main import _build_module_lookup


def test_build_module_lookup_ignores_unhashable_slug_values():
    """A damaged module slug must not make unrelated pages return HTTP 500."""

    valid_module = {"slug": "continuity", "enabled": True}

    result = _build_module_lookup(
        [
            valid_module,
            {"slug": {"unexpected": "object"}, "enabled": True},
            {"slug": ["unexpected", "list"], "enabled": True},
            {"slug": "", "enabled": True},
            None,
        ]
    )

    assert result == {"continuity": valid_module}


def test_build_module_lookup_preserves_trimmed_nonempty_slug_keys():
    """Valid slugs retain their database value and module metadata."""

    module = {"slug": "voice-monitor", "enabled": False, "settings": {}}

    assert _build_module_lookup([module]) == {"voice-monitor": module}
