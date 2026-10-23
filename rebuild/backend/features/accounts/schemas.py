from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=4096)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if value.count("@") != 1 or any(c.isspace() for c in value):
            raise ValueError("Invalid email identifier")
        return value


class HatcheryAccess(BaseModel):
    id: UUID
    name: str


class OperatorResponse(BaseModel):
    id: UUID
    email: str | None
    role: Literal["operator"] = "operator"
    hatcheries: list[HatcheryAccess]
    csrf_token: str


def operator_response(operator):
    return OperatorResponse(id=operator.id, email=operator.email,
                            hatcheries=operator.hatcheries, csrf_token=operator.csrf)
