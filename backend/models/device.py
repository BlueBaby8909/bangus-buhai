"""
Device model — tracks registered IoT devices and their online/offline status.

A Device record is created automatically the first time the MQTT subscriber
receives telemetry from that device_id. No manual registration step required.

The device_id is derived from the MAC address in the firmware:
  "BB-" + 6 bytes MAC hex = "BB-AABBCC112233"

This approach (auto-registration on first message) is appropriate for a
prototype. A production system would add a pre-registration step with
device certificates or API keys.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Unique per-device identifier derived from MAC address in firmware.
    # Format: "BB-AABBCC112233"
    device_id: str = Field(unique=True, index=True)

    # Which tank this device is monitoring (set from the tank_id in telemetry)
    tank_id: Optional[int] = Field(default=None, foreign_key="tankprofile.id")

    # Firmware version string reported in telemetry payload
    firmware_version: Optional[str] = None

    # Populated by the MQTT subscriber on every telemetry message
    last_seen: Optional[datetime] = None

    # Set to True on "online" status, False on "offline" / LWT
    is_online: bool = Field(default=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class DeviceRead(SQLModel):
    id: int
    device_id: str
    tank_id: Optional[int]
    firmware_version: Optional[str]
    last_seen: Optional[datetime]
    is_online: bool
    created_at: datetime
