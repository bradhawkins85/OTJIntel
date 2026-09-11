from __future__ import annotations

from typing import Any

from app.core.database import db


async def list_connections() -> list[dict[str, Any]]:
    rows = await db.fetch_all("SELECT * FROM dropbox_connections ORDER BY name, id")
    return [dict(row) for row in rows]


async def get_connection(connection_id: int) -> dict[str, Any] | None:
    row = await db.fetch_one("SELECT * FROM dropbox_connections WHERE id = ?", (connection_id,))
    return dict(row) if row else None


async def create_connection(data: dict[str, Any]) -> dict[str, Any]:
    connection_id = await db.execute_returning_lastrowid(
        """INSERT INTO dropbox_connections
           (name, app_key, app_secret_encrypted, refresh_token_encrypted, root_path, active, account_email)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data["name"], data["app_key"], data["app_secret_encrypted"],
         data.get("refresh_token_encrypted"), data.get("root_path", ""),
         1 if data.get("active", True) else 0, data.get("account_email")),
    )
    return await get_connection(connection_id)  # type: ignore[return-value]


async def update_connection(connection_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "app_key", "app_secret_encrypted", "refresh_token_encrypted", "root_path", "active", "account_email"}
    values = {key: value for key, value in data.items() if key in allowed}
    if not values:
        return await get_connection(connection_id)
    if "active" in values:
        values["active"] = 1 if values["active"] else 0
    assignments = ", ".join(f"{key} = ?" for key in values)
    await db.execute(
        f"UPDATE dropbox_connections SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*values.values(), connection_id),
    )
    return await get_connection(connection_id)


async def delete_connection(connection_id: int) -> None:
    await db.execute("DELETE FROM dropbox_connections WHERE id = ?", (connection_id,))


async def get_import(connection_id: int, folder_id: str) -> dict[str, Any] | None:
    row = await db.fetch_one(
        "SELECT * FROM dropbox_imports WHERE connection_id = ? AND dropbox_folder_id = ?",
        (connection_id, folder_id),
    )
    return dict(row) if row else None


async def record_import(*, connection_id: int, folder_id: str, path: str,
                        requester_email: str, subject: str, ticket_id: int | None,
                        status: str, error_message: str | None = None) -> dict[str, Any]:
    import_id = await db.execute_returning_lastrowid(
        """INSERT INTO dropbox_imports
           (connection_id, dropbox_folder_id, dropbox_path, requester_email, subject, ticket_id, status, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (connection_id, folder_id, path, requester_email, subject, ticket_id, status, error_message),
    )
    row = await db.fetch_one("SELECT * FROM dropbox_imports WHERE id = ?", (import_id,))
    return dict(row)


async def list_imports(connection_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = await db.fetch_all(
        "SELECT * FROM dropbox_imports WHERE connection_id = ? ORDER BY imported_at DESC, id DESC LIMIT ?",
        (connection_id, limit),
    )
    return [dict(row) for row in rows]
