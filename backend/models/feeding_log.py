from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class FeedType(str, Enum):
    PELLET = "pellet"
    NATURAL = "natural"
    SUPPLEMENT = "supplement"


class CreateFeedingLog(SQLModel):
    feed_type: FeedType
    amount_grams: float
    notes: Optional[str] = None


class FeedingLog(CreateFeedingLog, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tank_id: int = Field(foreign_key="tankprofile.id", index=True)
    fed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "serialize_in_order": True}
