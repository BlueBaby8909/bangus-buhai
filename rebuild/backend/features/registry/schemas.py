from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

DeviceID = Annotated[str, StringConstraints(strict=True, pattern=r"^BB-[0-9A-F]{12}$")]
Name = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200)]
T = TypeVar("T")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Named(Input):
    name: Name

    @field_validator("name")
    @classmethod
    def trimmed(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Empty name")
        return value


class Versioned(Input):
    expected_version: int = Field(ge=1, strict=True)


class RenameTank(Named, Versioned):
    pass


class RenameDevice(Versioned):
    display_name: Name | None

    @field_validator("display_name")
    @classmethod
    def trimmed(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Empty display name")
        return value


class Assignment(Versioned):
    tank_id: UUID | None


class ClaimStart(Input):
    device_id: DeviceID
    tank_id: UUID
    claim_code: SecretStr = Field(min_length=43, max_length=43)

    @field_validator("claim_code")
    @classmethod
    def valid_code(cls, value):
        from .security import decode
        if len(decode(value.get_secret_value())) != 32:
            raise ValueError("Invalid claim code")
        return value


class ChallengeRequest(Input):
    device_id: DeviceID
    purpose: Literal["sync", "confirm"]
    configuration_revision: int | None = Field(default=None, ge=1, strict=True)
    configuration_digest: Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")] | None = None


class ProofRequest(Input):
    challenge_id: UUID
    signature: SecretStr = Field(min_length=1, max_length=1024)


class TankResponse(BaseModel):
    id: UUID
    hatchery_id: UUID
    name: str
    version: int
    created_at: datetime
    archived_at: datetime | None


class BindingResponse(BaseModel):
    id: UUID
    device_id: UUID
    tank_id: UUID
    hatchery_id: UUID
    started_at: datetime
    ended_at: datetime | None


class ConfigurationDocument(BaseModel):
    schema_version: Literal[1]
    device_id: DeviceID
    hatchery_id: UUID
    tank_id: UUID | None
    binding_id: UUID | None
    archived: bool
    revision: int


class ConfigurationResponse(BaseModel):
    document: ConfigurationDocument
    digest: str
    confirmed_revision: int
    confirmed_at: datetime | None
    status: Literal["pending", "confirmed"]


class DeviceResponse(BaseModel):
    id: UUID
    device_id: DeviceID
    hatchery_id: UUID
    display_name: str | None
    version: int
    created_at: datetime
    archived_at: datetime | None
    verified: bool
    binding: BindingResponse | None
    configuration: ConfigurationResponse | None


class ClaimResponse(BaseModel):
    id: UUID
    device_id: DeviceID
    hatchery_id: UUID
    tank_id: UUID
    state: Literal["pending_proof", "awaiting_confirmation", "complete", "expired", "cancelled"]
    expires_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None


class ChallengeResponse(BaseModel):
    challenge_id: UUID
    payload: dict
    signing_input: str
    algorithm: Literal["RSA-PSS-SHA256"] = "RSA-PSS-SHA256"


class ProofResponse(BaseModel):
    state: Literal["unclaimed", "awaiting_confirmation", "complete"]
    configuration: ConfigurationResponse | None
