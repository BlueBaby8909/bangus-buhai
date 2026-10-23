from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, model_validator


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    type: Literal['relay.set', 'relay.auto']
    desired_on: bool | None = None

    @model_validator(mode='after')
    def action(self) -> Self:
        if (self.type == 'relay.set') != (self.desired_on is not None):
            raise ValueError('relay.set requires a Boolean; relay.auto has no desired state')
        return self
