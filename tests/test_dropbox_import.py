from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def app_secrets(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-with-at-least-32-characters")
    monkeypatch.setenv("TOTP_ENCRYPTION_KEY", "test-encryption-key-with-at-least-32-characters")


def test_dropbox_path_and_email_validation():
    from app.services.dropbox import _valid_email, normalise_root_path

    assert normalise_root_path(" /Ticket Imports/ ") == "/Ticket Imports"
    assert normalise_root_path("/") == ""
    with pytest.raises(ValueError):
        normalise_root_path("/imports/../private")
    assert _valid_email("Person@Example.com") == "person@example.com"
    assert _valid_email("not an email") is None


def test_public_connection_never_exposes_secrets():
    from app.services.dropbox import public_connection

    result = public_connection({
        "id": 7, "name": "Calls", "app_key": "key", "root_path": "/calls",
        "active": 1, "refresh_token_encrypted": "encrypted-refresh",
        "app_secret_encrypted": "encrypted-secret",
    })
    assert result["connected"] is True
    assert "app_secret_encrypted" not in result
    assert "refresh_token_encrypted" not in result


@pytest.mark.anyio
async def test_sync_imports_summary_and_all_files(monkeypatch):
    from app.services import dropbox as service

    connection = {"id": 1, "active": 1, "root_path": "/root"}
    client = AsyncMock()
    client.list_folder.side_effect = [
        [{".tag": "folder", "name": "person@example.com", "path_lower": "/root/person@example.com"}],
        [{".tag": "folder", "id": "id:ticket", "name": "Printer issue", "path_lower": "/root/person@example.com/printer"}],
        [
            {".tag": "file", "name": "call.m4a", "path_lower": "/call"},
            {".tag": "file", "name": "call_shortsummary.md", "path_lower": "/short"},
            {".tag": "file", "name": "call_transcript.txt", "path_lower": "/transcript"},
        ],
    ]
    client.download.side_effect = [(b"audio", "audio/x-m4a"), (b"Concise description", "text/markdown"), (b"Full transcript", "text/plain")]
    monkeypatch.setattr(service.dropbox_repo, "get_connection", AsyncMock(return_value=connection))
    monkeypatch.setattr(service.dropbox_repo, "get_import", AsyncMock(return_value=None))
    record_import = AsyncMock()
    monkeypatch.setattr(service.dropbox_repo, "record_import", record_import)
    monkeypatch.setattr(service, "_client_for", AsyncMock(return_value=client))
    monkeypatch.setattr(service.user_repo, "get_user_by_email", AsyncMock(return_value={"id": 9, "company_id": 3}))
    monkeypatch.setattr(service.tickets, "create_ticket", AsyncMock(return_value={"id": 42}))
    save_file = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(service.ticket_attachments, "save_file_bytes", save_file)

    result = await service.sync_connection(1, actor_user_id=2)

    assert result == {"created": 1, "skipped": 0, "failed": 0, "errors": []}
    assert service.tickets.create_ticket.await_args.kwargs["description"] == "Concise description"
    assert service.tickets.create_ticket.await_args.kwargs["subject"] == "Printer issue"
    assert save_file.await_count == 3
    assert record_import.await_args.kwargs["ticket_id"] == 42
