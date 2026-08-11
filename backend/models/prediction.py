from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


# 1. Base / Input Schema
class CreatePrediction(SQLModel):
    pass


# 2. Database Model
# Stores prediction history.
class Prediction(CreatePrediction, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    tank_id: int = Field(foreign_key="tankprofile.id", index=True)

    # 1-hour horizon
    temperature_1h: float
    pH_1h: float
    turbidity_1h: float
    
    # 2-hour horizon
    temperature_2h: float
    pH_2h: float
    turbidity_2h: float
    
    # 3-hour horizon
    temperature_3h: float
    pH_3h: float
    turbidity_3h: float
    
    # 4-hour horizon
    temperature_4h: float
    pH_4h: float
    turbidity_4h: float

    predicted_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "serialize_in_order": True,
    }


# 3. Response Model
class PredictionRead(SQLModel):
    id: int
    tank_id: int

    temperature_1h: float
    pH_1h: float
    turbidity_1h: float
    
    temperature_2h: float
    pH_2h: float
    turbidity_2h: float
    
    temperature_3h: float
    pH_3h: float
    turbidity_3h: float
    
    temperature_4h: float
    pH_4h: float
    turbidity_4h: float

    predicted_from: datetime
    confidence_score: float
    created_at: datetime