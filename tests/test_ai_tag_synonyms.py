from pathlib import Path

import pytest

from app.main import app
from app.repositories import ai_tag_synonyms as repo


def test_admin_and_crud_api_routes_are_registered():
    assert "/api/chat/ai-tag-synonyms" in app.openapi()["paths"]
    # Feature-pack routes are registered when startup loads feature packs.
    assert Path("app/features/ai_tag_synonyms/routes.py").is_file()


def test_validate_terms_normalises_and_deduplicates():
    assert repo.validate_terms([" Wi-Fi ", "wireless", "wi_fi", ""]) == ["wi fi", "wireless"]


def test_validate_terms_rejects_less_than_two_unique_terms():
    with pytest.raises(repo.InvalidSynonymGroup):
        repo.validate_terms(["monitor", "monitor"])


def test_api_schema_documents_full_crud():
    schema_paths = app.openapi()["paths"]
    assert set(schema_paths["/api/chat/ai-tag-synonyms"]) >= {"get", "post"}
    assert set(schema_paths["/api/chat/ai-tag-synonyms/{group_id}"]) >= {"get", "put", "delete"}
