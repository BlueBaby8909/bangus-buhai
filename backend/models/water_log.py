from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field

# Base schema for client input (keeps requests clean by omitting DB-generated fields like ID and tank_id)
class CreateWaterLog(SQLModel):
    temperature: float
    pH: float
    turbidity: float
    notes: Optional[str] = None


# Database table model — inherits water metrics from CreateWaterLog and adds relational/DB fields
class WaterLog(CreateWaterLog, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tank_id: int = Field(foreign_key="tankprofile.id", index=True)
    device_id: Optional[str] = Field(default=None, foreign_key="device.device_id", index=True)
    ph_source: str = Field(default="manual")
    relay_on: bool = Field(default=False)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "serialize_in_order": True}


class WaterLogRead(SQLModel):
    """Response shape for a water log, enriched with a computed water-quality status
    so the frontend doesn't have to re-implement the thresholds itself."""
    id: int
    tank_id: int
    temperature: float
    pH: float
    turbidity: float
    notes: Optional[str] = None
    ph_source: str
    ph_is_estimated: bool
    relay_on: bool
    recorded_at: datetime
    status: str
    warnings: list[str]
