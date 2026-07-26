from fastapi import APIRouter, Depends, Query, status
from models.water_log import CreateWaterLog, WaterLogRead
import services.waterlog_services as service

from sqlmodel import Session
from database.db import get_session

router = APIRouter()


# create log entry for a tank
@router.post("/{tank_id}/logs", response_model=WaterLogRead, status_code=status.HTTP_201_CREATED)
def create_water_log(tank_id: int, waterlog: CreateWaterLog, db: Session = Depends(get_session)):
    return service.create_water_log(tank_id=tank_id, log=waterlog, db=db)


# view all logs across all tanks
# static routes must be declared before the dynamic "/{tank_id}/logs" route below,
# otherwise FastAPI tries to parse "all" as a tank_id
@router.get("/logs/all", response_model=list[WaterLogRead], status_code=status.HTTP_200_OK)
def get_all_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return service.get_all_logs(skip=skip, limit=limit, db=db)


# view all logs for one tank
@router.get("/{tank_id}/logs", response_model=list[WaterLogRead], status_code=status.HTTP_200_OK)
def get_all_logs_for_tank(
    tank_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return service.get_all_logs_for_tank(tank_id=tank_id, skip=skip, limit=limit, db=db)


# view a single log from one tank
@router.get("/{tank_id}/logs/{log_id}", response_model=WaterLogRead, status_code=status.HTTP_200_OK)
def get_log(tank_id: int, log_id: int, db: Session = Depends(get_session)):
    return service.get_log(tank_id=tank_id, log_id=log_id, db=db)


# update a log from one tank
@router.put("/{tank_id}/logs/{log_id}", response_model=WaterLogRead, status_code=status.HTTP_200_OK)
def update_log(tank_id: int, log_id: int, log_data: CreateWaterLog, db: Session = Depends(get_session)):
    return service.update_log(tank_id=tank_id, log_id=log_id, log_data=log_data, db=db)


# delete a log
@router.delete("/{tank_id}/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(tank_id: int, log_id: int, db: Session = Depends(get_session)):
    return service.delete_log(tank_id=tank_id, log_id=log_id, db=db)
