from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetCreate(BaseModel):
    """Fields accepted when manually adding an asset."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    type: Optional[str] = Field(default=None, max_length=100)
    machine_type: Optional[str] = Field(default=None, max_length=255)
    serial_number: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, max_length=100)
    os_name: Optional[str] = Field(default=None, max_length=255)
    cpu_name: Optional[str] = Field(default=None, max_length=255)
    ram_gb: Optional[float] = Field(default=None, ge=0)
    hdd_size: Optional[str] = Field(default=None, max_length=100)
    boot_time: Optional[datetime] = None
    motherboard_manufacturer: Optional[str] = Field(default=None, max_length=255)
    form_factor: Optional[str] = Field(default=None, max_length=100)
    last_user: Optional[str] = Field(default=None, max_length=255)
    approx_age: Optional[float] = Field(default=None, ge=0)
    performance_score: Optional[float] = Field(default=None, ge=0)
    warranty_status: Optional[str] = Field(default=None, max_length=100)
    warranty_end_date: Optional[date] = None
    mac_address: Optional[str] = Field(default=None, max_length=64)


class AssetResponse(BaseModel):
    id: int
    company_id: int
    name: str
    type: Optional[str] = None
    machine_type: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = None
    os_name: Optional[str] = None
    cpu_name: Optional[str] = None
    ram_gb: Optional[float] = None
    hdd_size: Optional[str] = None
    last_sync: Optional[datetime] = None
    boot_time: Optional[datetime] = None
    motherboard_manufacturer: Optional[str] = None
    form_factor: Optional[str] = None
    last_user: Optional[str] = None
    approx_age: Optional[float] = None
    performance_score: Optional[float] = None
    warranty_status: Optional[str] = None
    warranty_end_date: Optional[date] = None
    tactical_asset_id: Optional[str] = None
    tray_device_uid: Optional[str] = None
