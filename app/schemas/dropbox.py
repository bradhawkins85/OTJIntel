from datetime import datetime

from pydantic import BaseModel, Field


class DropboxConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    app_key: str = Field(min_length=1, max_length=255)
    app_secret: str = Field(min_length=1, max_length=1024)
    root_path: str = Field(default="", max_length=1024)
    active: bool = True


class DropboxConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    app_key: str | None = Field(default=None, min_length=1, max_length=255)
    app_secret: str | None = Field(default=None, max_length=1024)
    root_path: str | None = Field(default=None, max_length=1024)
    active: bool | None = None


class DropboxConnectionResponse(BaseModel):
    id: int
    name: str
    app_key: str
    root_path: str
    active: bool
    connected: bool
    account_email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DropboxSyncResponse(BaseModel):
    created: int
    skipped: int
    failed: int
    errors: list[dict[str, str]]

