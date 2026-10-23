from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.features.accounts.router import current_operator
from backend.features.accounts.service import Operator
from .schemas import (Assignment, BindingResponse, ChallengeRequest, ChallengeResponse, ClaimResponse,
    ClaimStart, DeviceResponse, Named, Page, ProofRequest, ProofResponse, RenameDevice, RenameTank,
    TankResponse, Versioned)
from .service import RegistryService

router = APIRouter(prefix="/api/v1/hatcheries/{hatchery_id}", tags=["registry"])
device_router = APIRouter(prefix="/api/device/v1", tags=["device setup"])
ExternalID = Annotated[str, Path(pattern=r"^BB-[0-9A-F]{12}$")]
Limit = Annotated[int, Query(ge=1, le=200)]
Cursor = Annotated[str | None, Query(max_length=512)]


def registry(request: Request):
    runtime = request.app.state.account_runtime
    accounts = runtime.get()
    return RegistryService(accounts.engine, accounts.settings.token_key, accounts.clock)


Registry = Annotated[RegistryService, Depends(registry)]
Authenticated = Annotated[Operator, Depends(current_operator)]


def client_ip(request):
    return request.client.host if request.client else "unknown"


@router.post("/tanks", response_model=TankResponse, status_code=201)
def create_tank(hatchery_id: UUID, body: Named, operator: Authenticated, service: Registry):
    return service.create_tank(hatchery_id, operator.id, body.name)


@router.get("/tanks", response_model=Page[TankResponse])
def tanks(hatchery_id: UUID, operator: Authenticated, service: Registry,
          limit: Limit = 50, cursor: Cursor = None, include_archived: bool = False):
    return service.tanks(hatchery_id, operator.id, limit, cursor, include_archived)


@router.get("/tanks/{tank_id}", response_model=TankResponse)
def tank(hatchery_id: UUID, tank_id: UUID, operator: Authenticated, service: Registry):
    return service.get_tank(hatchery_id, operator.id, tank_id)


@router.patch("/tanks/{tank_id}", response_model=TankResponse)
def rename_tank(hatchery_id: UUID, tank_id: UUID, body: RenameTank, operator: Authenticated, service: Registry):
    return service.change_tank(hatchery_id, operator.id, tank_id, body.expected_version, name=body.name)


@router.post("/tanks/{tank_id}/archive", response_model=TankResponse)
def archive_tank(hatchery_id: UUID, tank_id: UUID, body: Versioned, operator: Authenticated, service: Registry):
    return service.change_tank(hatchery_id, operator.id, tank_id, body.expected_version, archive=True)


@router.post("/tanks/{tank_id}/restore", response_model=TankResponse)
def restore_tank(hatchery_id: UUID, tank_id: UUID, body: Versioned, operator: Authenticated, service: Registry):
    return service.change_tank(hatchery_id, operator.id, tank_id, body.expected_version, archive=False)


@router.get("/devices", response_model=Page[DeviceResponse])
def devices(hatchery_id: UUID, operator: Authenticated, service: Registry,
            limit: Limit = 50, cursor: Cursor = None, include_archived: bool = False):
    return service.devices(hatchery_id, operator.id, limit, cursor, include_archived)


@router.get("/devices/{device_id}", response_model=DeviceResponse)
def device(hatchery_id: UUID, device_id: ExternalID, operator: Authenticated, service: Registry):
    return service.get_device(hatchery_id, operator.id, device_id)


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
def rename_device(hatchery_id: UUID, device_id: ExternalID, body: RenameDevice,
                  operator: Authenticated, service: Registry):
    return service.change_device(hatchery_id, operator.id, device_id, body.expected_version, display_name=body.display_name)


@router.post("/devices/{device_id}/archive", response_model=DeviceResponse)
def archive_device(hatchery_id: UUID, device_id: ExternalID, body: Versioned, operator: Authenticated, service: Registry):
    return service.change_device(hatchery_id, operator.id, device_id, body.expected_version, archive=True)


@router.post("/devices/{device_id}/restore", response_model=DeviceResponse)
def restore_device(hatchery_id: UUID, device_id: ExternalID, body: Versioned, operator: Authenticated, service: Registry):
    return service.change_device(hatchery_id, operator.id, device_id, body.expected_version, archive=False)


@router.post("/devices/{device_id}/assignment", response_model=DeviceResponse)
def assign(hatchery_id: UUID, device_id: ExternalID, body: Assignment, operator: Authenticated, service: Registry):
    return service.assign(hatchery_id, operator.id, device_id, body.tank_id, body.expected_version)


@router.get("/devices/{device_id}/bindings", response_model=Page[BindingResponse])
def bindings(hatchery_id: UUID, device_id: ExternalID, operator: Authenticated, service: Registry,
             limit: Limit = 50, cursor: Cursor = None):
    return service.bindings(hatchery_id, operator.id, device_id, limit, cursor)


@router.post("/device-claims", response_model=ClaimResponse, status_code=201)
def start_claim(hatchery_id: UUID, body: ClaimStart, request: Request, operator: Authenticated, service: Registry):
    return service.start_claim(hatchery_id, operator.id, body.device_id, body.tank_id,
        body.claim_code.get_secret_value(), client_ip(request))


@router.get("/device-claims/{claim_id}", response_model=ClaimResponse)
def claim(hatchery_id: UUID, claim_id: UUID, operator: Authenticated, service: Registry):
    return service.get_claim(hatchery_id, operator.id, claim_id)


@router.post("/device-claims/{claim_id}/cancel", response_model=ClaimResponse)
def cancel_claim(hatchery_id: UUID, claim_id: UUID, operator: Authenticated, service: Registry):
    return service.get_claim(hatchery_id, operator.id, claim_id, cancel=True)


@device_router.post("/challenges", response_model=ChallengeResponse)
def challenge(body: ChallengeRequest, request: Request, service: Registry):
    return service.challenge(body.device_id, body.purpose, body.configuration_revision,
        body.configuration_digest, client_ip(request))


@device_router.post("/proofs", response_model=ProofResponse)
def proof(body: ProofRequest, request: Request, service: Registry):
    return service.proof(body.challenge_id, body.signature.get_secret_value(), client_ip(request))
