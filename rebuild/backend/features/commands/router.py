from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Path, Request
from backend.features.accounts.router import current_operator
from backend.features.accounts.service import Operator
from .schemas import CommandRequest
from .service import CommandService

router = APIRouter(prefix='/api/v1/hatcheries/{hatchery_id}/devices/{device_id}/commands', tags=['commands'])
ExternalID = Annotated[str, Path(pattern=r'^BB-[0-9A-F]{12}$')]


def commands(request: Request):
    accounts = request.app.state.account_runtime.get()
    return CommandService(accounts.engine, accounts.settings.token_key, accounts.clock)


@router.post('', status_code=202)
def create(hatchery_id: UUID, device_id: ExternalID, body: CommandRequest,
           key: Annotated[UUID, Header(alias='Idempotency-Key')],
           operator: Annotated[Operator, Depends(current_operator)],
           service: Annotated[CommandService, Depends(commands)]):
    service.registry.throttle('commands', [('actor', str(operator.id)), ('device', device_id)])
    return service.create(hatchery_id, device_id, operator.id, key, body)


@router.get('/latest')
def latest(hatchery_id: UUID, device_id: ExternalID,
           operator: Annotated[Operator, Depends(current_operator)],
           service: Annotated[CommandService, Depends(commands)]):
    return service.latest(hatchery_id, device_id, operator.id)


@router.get('/{command_id}')
def detail(hatchery_id: UUID, device_id: ExternalID, command_id: UUID,
           operator: Annotated[Operator, Depends(current_operator)],
           service: Annotated[CommandService, Depends(commands)]):
    return service.detail(hatchery_id, device_id, operator.id, command_id)
