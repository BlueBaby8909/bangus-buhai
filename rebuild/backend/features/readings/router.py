from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.features.accounts.router import current_operator
from backend.features.accounts.service import Operator
from .schemas import (CorrectMeasurement, CreateMeasurement, HistoryResponse, ManualResponse,
    ReadingResponse, RevisionAction, RevisionsResponse, Timestamp)
from .service import ReadingsService

router = APIRouter(prefix="/api/v1/hatcheries/{hatchery_id}/tanks/{tank_id}", tags=["readings"])
Limit = Annotated[int, Query(ge=1, le=200)]
Authenticated = Annotated[Operator, Depends(current_operator)]


def readings(request: Request):
    accounts = request.app.state.account_runtime.get()
    return ReadingsService(accounts.engine, accounts.settings.token_key, accounts.clock)


Readings = Annotated[ReadingsService, Depends(readings)]


@router.get("/readings", response_model=HistoryResponse)
def history(hatchery_id: UUID, tank_id: UUID, operator: Authenticated, service: Readings,
            limit: Limit = 50, cursor: Annotated[str | None, Query(max_length=4096)] = None,
            time_basis: Literal["measured", "received"] = "measured", origin: Literal["all", "manual", "device"] = "all",
            include_voided: bool = False, since: Timestamp | None = None, until: Timestamp | None = None):
    return service.history(hatchery_id, tank_id, operator.id, limit=limit, cursor=cursor,
        time_basis=time_basis, origin=origin, include_voided=include_voided, since=since, until=until)


@router.get("/readings/{origin}/{reading_id}", response_model=ReadingResponse)
def detail(hatchery_id: UUID, tank_id: UUID, origin: Literal["device", "manual"], reading_id: UUID,
           operator: Authenticated, service: Readings):
    return service.detail(hatchery_id, tank_id, operator.id, origin, reading_id)


@router.post("/manual-readings", response_model=ManualResponse, status_code=201)
def create(hatchery_id: UUID, tank_id: UUID, body: CreateMeasurement, response: Response,
           operator: Authenticated, service: Readings):
    reading, created = service.create(hatchery_id, tank_id, operator.id, body)
    response.status_code = 201 if created else 200
    return reading


@router.patch("/manual-readings/{reading_id}", response_model=ManualResponse)
def correct(hatchery_id: UUID, tank_id: UUID, reading_id: UUID, body: CorrectMeasurement,
            operator: Authenticated, service: Readings):
    return service.change(hatchery_id, tank_id, operator.id, reading_id, body, "correct")


@router.post("/manual-readings/{reading_id}/void", response_model=ManualResponse)
def void(hatchery_id: UUID, tank_id: UUID, reading_id: UUID, body: RevisionAction,
         operator: Authenticated, service: Readings):
    return service.change(hatchery_id, tank_id, operator.id, reading_id, body, "void")


@router.post("/manual-readings/{reading_id}/restore", response_model=ManualResponse)
def restore(hatchery_id: UUID, tank_id: UUID, reading_id: UUID, body: RevisionAction,
            operator: Authenticated, service: Readings):
    return service.change(hatchery_id, tank_id, operator.id, reading_id, body, "restore")


@router.get("/manual-readings/{reading_id}/revisions", response_model=RevisionsResponse)
def revisions(hatchery_id: UUID, tank_id: UUID, reading_id: UUID, operator: Authenticated, service: Readings,
              limit: Limit = 50, before_version: Annotated[int | None, Query(ge=1)] = None):
    return service.revisions(hatchery_id, tank_id, operator.id, reading_id, limit, before_version)
