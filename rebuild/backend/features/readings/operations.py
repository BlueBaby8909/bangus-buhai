"""Hatchery overview and export HTTP interfaces."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse
from backend.features.accounts.router import current_operator
from backend.features.accounts.service import Operator
from .router import readings
from .service import ReadingsService
from .schemas import Timestamp, SummaryResponse
from .overview import overview
from .export import prepare

router = APIRouter(prefix='/api/v1/hatcheries/{hatchery_id}', tags=['readings'])


@router.get('/tank-summaries', response_model=SummaryResponse)
def summaries(hatchery_id: UUID, operator: Annotated[Operator, Depends(current_operator)],
              service: Annotated[ReadingsService, Depends(readings)], limit: int = Query(25, ge=1, le=100),
              cursor: str | None = Query(None, max_length=512), include_archived: bool = False):
    return overview(service, hatchery_id, operator.id, limit, cursor, include_archived)


@router.get('/readings/export')
def export(hatchery_id: UUID, request: Request, operator: Annotated[Operator, Depends(current_operator)],
           service: Annotated[ReadingsService, Depends(readings)], tank_id: UUID | None = None,
           time_basis: Literal['received','measured'] = 'received', origin: Literal['all','manual','device'] = 'all',
           include_voided: bool = False, since: Timestamp | None = None, until: Timestamp | None = None):
    accounts = request.app.state.account_runtime.get()
    content = prepare(service, accounts, request.cookies.get(accounts.settings.cookie_name), hatchery_id,
        operator.id, tank_id, dict(time_basis=time_basis, origin=origin, include_voided=include_voided, since=since, until=until))
    return StreamingResponse(content, media_type='text/csv', headers={
        'Content-Disposition':'attachment; filename="bangus-readings.csv"', 'Cache-Control':'no-store'})
