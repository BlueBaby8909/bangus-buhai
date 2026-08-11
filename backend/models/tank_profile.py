from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class GrowthStage(str, Enum):
    """Standard bangus (milkfish) rearing stages."""
    FRY = "fry"
    FINGERLING = "fingerling"
    JUVENILE = "juvenile"
    ADULT = "adult"


# 1. Base / Input Schema (What the client sends in JSON when creating a tank)
class CreateTankProfile(SQLModel):
    name: str
    volume_ml: float
    growth_stage: GrowthStage


# 2. Database Model (Inherits tank fields + adds DB metadata)
class TankProfile(CreateTankProfile, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # capacity is server-computed (see services/tank_services.py), never client-supplied
    capacity: float = Field(default=0)
    date_added: date = Field(default_factory=date.today)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "serialize_in_order": True}
