from __future__ import annotations

import base64
import json
import mimetypes
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import httpx
from email_validator import EmailNotValidError, validate_email

from app.repositories import dropbox as dropbox_repo
from app.repositories import staff as staff_repo
from app.repositories import users as user_repo
from app.security.encryption import decrypt_secret, encrypt_secret
from app.services import ticket_attachments, tickets

API_URL = "https://api.dropboxapi.com/2"
CONTENT_URL = "https://content.dropboxapi.com/2"
TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
ALLOWED_EXTENSIONS = {".m4a", ".txt", ".md", ".markdown"}
MAX_FILES_PER_TICKET = 10


@dataclass(slots=True)
class DropboxClient:
    access_token: str

    async def rpc(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{API_URL}/{endpoint}", json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        response.raise_for_status()
        return response.json()

    async def list_folder(self, path: str) -> list[dict[str, Any]]:
        result = await self.rpc("files/list_folder", {"path": path, "recursive": False})
        entries = list(result.get("entries", []))
        while result.get("has_more"):
            result = await self.rpc("files/list_folder/continue", {"cursor": result["cursor"]})
            entries.extend(result.get("entries", []))
        return entries

    async def download(self, path: str) -> tuple[bytes, str | None]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{CONTENT_URL}/files/download",
                headers={"Authorization": f"Bearer {self.access_token}", "Dropbox-API-Arg": json.dumps({"path": path})},
            )
        response.raise_for_status()
        return response.content, response.headers.get("content-type")


def public_connection(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(record["id"]), "name": record["name"], "app_key": record["app_key"],
        "root_path": record.get("root_path") or "", "active": bool(record.get("active")),
        "connected": bool(record.get("refresh_token_encrypted")),
        "account_email": record.get("account_email"), "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def normalise_root_path(value: str) -> str:
    value = value.strip()
    if not value or value == "/":
        return ""
    path = "/" + value.strip("/")
    if ".." in PurePosixPath(path).parts:
        raise ValueError("Dropbox folder path cannot contain '..'.")
    return path


async def create_connection(data: dict[str, Any]) -> dict[str, Any]:
    name, key, secret = (str(data.get(field) or "").strip() for field in ("name", "app_key", "app_secret"))
    if not all((name, key, secret)):
        raise ValueError("Name, Dropbox app key, and app secret are required.")
    record = await dropbox_repo.create_connection({
        "name": name, "app_key": key, "app_secret_encrypted": encrypt_secret(secret),
        "root_path": normalise_root_path(str(data.get("root_path") or "")),
        "active": bool(data.get("active", True)),
    })
    return public_connection(record)


async def update_connection(connection_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    updates: dict[str, Any] = {}
    for key in ("name", "app_key"):
        if key in data:
            value = str(data[key] or "").strip()
            if not value:
                raise ValueError(f"{key.replace('_', ' ').title()} is required.")
            updates[key] = value
    if data.get("app_secret"):
        updates["app_secret_encrypted"] = encrypt_secret(str(data["app_secret"]).strip())
    if "root_path" in data:
        updates["root_path"] = normalise_root_path(str(data["root_path"] or ""))
    if "active" in data:
        updates["active"] = bool(data["active"])
    record = await dropbox_repo.update_connection(connection_id, updates)
    return public_connection(record) if record else None


async def exchange_authorization_code(connection_id: int, code: str, redirect_uri: str) -> dict[str, Any]:
    record = await dropbox_repo.get_connection(connection_id)
    if not record:
        raise ValueError("Dropbox connection not found.")
    credentials = base64.b64encode(
        f"{record['app_key']}:{decrypt_secret(record['app_secret_encrypted'])}".encode()
    ).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(TOKEN_URL, data={"code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri}, headers={"Authorization": f"Basic {credentials}"})
    response.raise_for_status()
    token = response.json()
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise ValueError("Dropbox did not return an offline refresh token.")
    client = DropboxClient(str(token["access_token"]))
    account = await client.rpc("users/get_current_account", {})
    updated = await dropbox_repo.update_connection(connection_id, {
        "refresh_token_encrypted": encrypt_secret(str(refresh_token)),
        "account_email": account.get("email"),
    })
    return public_connection(updated)  # type: ignore[arg-type]


async def _client_for(record: dict[str, Any]) -> DropboxClient:
    refresh = record.get("refresh_token_encrypted")
    if not refresh:
        raise ValueError("Connect this configuration to Dropbox before importing.")
    credentials = base64.b64encode(
        f"{record['app_key']}:{decrypt_secret(record['app_secret_encrypted'])}".encode()
    ).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(TOKEN_URL, data={"refresh_token": decrypt_secret(refresh), "grant_type": "refresh_token"}, headers={"Authorization": f"Basic {credentials}"})
    response.raise_for_status()
    return DropboxClient(str(response.json()["access_token"]))


def _valid_email(folder_name: str) -> str | None:
    try:
        return validate_email(folder_name, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


async def sync_connection(connection_id: int, *, actor_user_id: int | None = None) -> dict[str, Any]:
    connection = await dropbox_repo.get_connection(connection_id)
    if not connection:
        raise ValueError("Dropbox connection not found.")
    if not connection.get("active"):
        raise ValueError("Dropbox connection is disabled.")
    client = await _client_for(connection)
    result: dict[str, Any] = {"created": 0, "skipped": 0, "failed": 0, "errors": []}
    requester_folders = await client.list_folder(connection.get("root_path") or "")
    for requester_folder in requester_folders:
        if requester_folder.get(".tag") != "folder":
            continue
        email = _valid_email(str(requester_folder.get("name") or ""))
        if not email:
            result["skipped"] += 1
            continue
        ticket_folders = await client.list_folder(requester_folder["path_lower"])
        for folder in ticket_folders:
            if folder.get(".tag") != "folder":
                continue
            folder_id = str(folder.get("id") or folder["path_lower"])
            if await dropbox_repo.get_import(connection_id, folder_id):
                result["skipped"] += 1
                continue
            subject = str(folder.get("name") or "Dropbox import").strip()[:500]
            try:
                files = [entry for entry in await client.list_folder(folder["path_lower"]) if entry.get(".tag") == "file"]
                if not files or len(files) > MAX_FILES_PER_TICKET:
                    raise ValueError(f"Ticket folder must contain 1-{MAX_FILES_PER_TICKET} files.")
                unsupported = [f["name"] for f in files if PurePosixPath(f["name"]).suffix.lower() not in ALLOWED_EXTENSIONS]
                if unsupported:
                    raise ValueError("Unsupported file(s): " + ", ".join(unsupported))
                payloads: list[tuple[dict[str, Any], bytes, str | None]] = []
                description = None
                for file in files:
                    contents, content_type = await client.download(file["path_lower"])
                    payloads.append((file, contents, content_type))
                    stem = PurePosixPath(file["name"]).stem.lower()
                    if stem.endswith("_shortsummary"):
                        description = contents.decode("utf-8-sig", errors="replace").strip()
                if description is None:
                    raise ValueError("Ticket folder is missing a _shortsummary.txt or _shortsummary.md file.")
                requester = await user_repo.get_user_by_email(email)
                staff = None if requester else await staff_repo.get_staff_by_email(email)
                ticket = await tickets.create_ticket(
                    subject=subject, description=description, requester_id=requester.get("id") if requester else None,
                    requester_staff_id=staff.get("id") if staff else None,
                    company_id=(requester.get("company_id") if requester else None) or (staff.get("company_id") if staff else None),
                    assigned_user_id=None, priority="normal", status=None, category="Dropbox import",
                    module_slug="dropbox", external_reference=f"dropbox:{connection_id}:{folder_id}",
                    requester_email=email, initial_reply_author_email=email,
                    initial_reply_author_display_name=email,
                )
                ticket_id = int(ticket["id"])
                for file, contents, content_type in payloads:
                    guessed = mimetypes.guess_type(file["name"])[0]
                    await ticket_attachments.save_file_bytes(
                        ticket_id, contents=contents, original_filename=file["name"],
                        mime_type=(content_type or guessed or "application/octet-stream").split(";")[0],
                        access_level="open", uploaded_by_user_id=actor_user_id,
                    )
                await dropbox_repo.record_import(connection_id=connection_id, folder_id=folder_id,
                    path=folder["path_lower"], requester_email=email, subject=subject,
                    ticket_id=ticket_id, status="completed")
                result["created"] += 1
            except Exception as exc:
                await dropbox_repo.record_import(connection_id=connection_id, folder_id=folder_id,
                    path=folder.get("path_lower", ""), requester_email=email, subject=subject,
                    ticket_id=None, status="failed", error_message=str(exc)[:2000])
                result["failed"] += 1
                result["errors"].append({"folder": subject, "error": str(exc)})
    return result
