from fastapi import APIRouter, Depends, Query, status
from models.tank_profile import CreateTankProfile, TankProfile
import services.tank_services as service
import services.dashboard_services as dashboard_service

from sqlmodel import Session
from database.db import get_session


router = APIRouter()


@router.post("/", response_model=TankProfile, status_code=status.HTTP_201_CREATED)
def create_tank(tank_profile: CreateTankProfile, db: Session = Depends(get_session)):
    return service.create_tank(tank_profile=tank_profile, db=db)


@router.get("/", response_model=list[TankProfile], status_code=status.HTTP_200_OK)
def get_all_tanks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return service.get_all_tanks(skip=skip, limit=limit, db=db)


@router.get("/{tank_id}", response_model=TankProfile, status_code=status.HTTP_200_OK)
def view_tank(tank_id: int, db: Session = Depends(get_session)):
    return service.view_tank(tank_id=tank_id, db=db)


@router.get("/{tank_id}/summary", status_code=status.HTTP_200_OK)
def get_tank_summary(tank_id: int, db: Session = Depends(get_session)):
    """At-a-glance view: tank info + latest water reading + latest feeding + counts."""
    return dashboard_service.get_tank_summary(tank_id=tank_id, db=db)


@router.put("/{tank_id}", response_model=TankProfile, status_code=status.HTTP_200_OK)
def update_tank(
    tank_id: int, tank_data: CreateTankProfile, db: Session = Depends(get_session)
):
    return service.update_tank(tank_id=tank_id, tank_data=tank_data, db=db)


@router.delete("/{tank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tank(tank_id: int, db: Session = Depends(get_session)):
    return service.delete_tank(tank_id=tank_id, db=db)
