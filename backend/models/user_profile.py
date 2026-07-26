from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

# NOTE: table models must set table=True or SQLModel treats them as a plain
# pydantic schema and no table gets created -> requests blow up with a 500.


class CreateUser(SQLModel):
    name: str
    email: str


class User(CreateUser, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # unique=True stops duplicate accounts sharing an email; index speeds up lookups
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "serialize_in_order": True}
