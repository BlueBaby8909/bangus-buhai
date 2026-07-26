from fastapi import APIRouter, Depends, Query, status
from models.feeding_log import CreateFeedingLog, FeedingLog
import services.feeding_services as service

from sqlmodel import Session
from database.db import get_session

router = APIRouter()


@router.post("/{tank_id}/feedings", response_model=FeedingLog, status_code=status.HTTP_201_CREATED)
def create_feeding_log(tank_id: int, feeding: CreateFeedingLog, db: Session = Depends(get_session)):
    return service.create_feeding_log(tank_id=tank_id, feeding=feeding, db=db)


@router.get("/{tank_id}/feedings", response_model=list[FeedingLog], status_code=status.HTTP_200_OK)
def get_all_feeding_logs_for_tank(
    tank_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return service.get_all_feeding_logs_for_tank(tank_id=tank_id, skip=skip, limit=limit, db=db)


@router.get("/{tank_id}/feedings/{feeding_id}", response_model=FeedingLog, status_code=status.HTTP_200_OK)
def get_feeding_log(tank_id: int, feeding_id: int, db: Session = Depends(get_session)):
    return service.get_feeding_log(tank_id=tank_id, feeding_id=feeding_id, db=db)


@router.delete("/{tank_id}/feedings/{feeding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feeding_log(tank_id: int, feeding_id: int, db: Session = Depends(get_session)):
    return service.delete_feeding_log(tank_id=tank_id, feeding_id=feeding_id, db=db)
