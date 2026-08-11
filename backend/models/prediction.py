from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


# 1. Base / Input Schema
# (No client input needed yet, but keeping the same pattern
# makes it easy to extend later if predictions can be created manually.)
class CreatePrediction(SQLModel):
    pass


# 2. Database Model
# Stores prediction history.
class Prediction(CreatePrediction, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    tank_id: int = Field(foreign_key="tankprofile.id", index=True)

    temperature: float
    pH: float
    turbidity: float

    predicted_for: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "serialize_in_order": True,
    }


# 3. Response Model
class PredictionRead(SQLModel):
    id: int
    tank_id: int

    temperature: float
    pH: float
    turbidity: float

    predicted_for: datetime
    created_at: datetime