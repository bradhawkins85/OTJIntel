import sqlite3
from pathlib import Path

from app.core.database import Database


MIGRATION_PATH = Path("migrations/009_seed_account_email_templates.sql")


def _apply_migration(connection: sqlite3.Connection) -> None:
    database = Database()
    sql = database._adapt_sql_for_sqlite(MIGRATION_PATH.read_text(encoding="utf-8"))
    for statement in database._split_sql_statements(sql):
        connection.execute(statement)
    connection.commit()


def test_account_email_templates_are_seeded_idempotently() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR(120) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            content_type VARCHAR(40) NOT NULL,
            content TEXT NOT NULL
        )
        """
    )

    _apply_migration(connection)
    _apply_migration(connection)

    records = connection.execute(
        "SELECT slug, name, content_type, content FROM message_templates ORDER BY slug"
    ).fetchall()
    assert len(records) == 2
    assert records[0][:3] == ("signup_verification", "Email Verification", "text/html")
    assert "{{ verification.link }}" in records[0][3]
    assert records[1][:3] == ("staff_invitation", "Staff Invitation", "text/html")
    assert "{{ invitation.link }}" in records[1][3]


def test_account_email_template_seed_preserves_existing_customisation() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE message_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR(120) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            content_type VARCHAR(40) NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO message_templates (slug, name, description, content_type, content)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("staff_invitation", "Custom Invitation", None, "text/plain", "Custom body"),
    )

    _apply_migration(connection)

    invitation = connection.execute(
        "SELECT name, content_type, content FROM message_templates WHERE slug = ?",
        ("staff_invitation",),
    ).fetchone()
    assert invitation == ("Custom Invitation", "text/plain", "Custom body")
    assert connection.execute(
        "SELECT COUNT(*) FROM message_templates WHERE slug = ?",
        ("signup_verification",),
    ).fetchone() == (1,)
