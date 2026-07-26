from fastapi import HTTPException
from models.water_log import CreateWaterLog, WaterLog, WaterLogRead
from models.tank_profile import TankProfile
from sqlmodel import Session, select

from services.water_quality import evaluate_water_log


def _get_tank_or_404(tank_id: int, db: Session) -> TankProfile:
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return tank


def create_water_log(tank_id: int, log: CreateWaterLog, db: Session) -> WaterLogRead:
    _get_tank_or_404(tank_id, db)

    log_db = WaterLog.model_validate(log, update={"tank_id": tank_id})
    db.add(log_db)
    db.commit()
    db.refresh(log_db)
    return evaluate_water_log(log_db)


def get_all_logs(db: Session, skip: int = 0, limit: int = 10) -> list[WaterLogRead]:
    logs = db.exec(select(WaterLog).offset(skip).limit(limit)).all()
    return [evaluate_water_log(log) for log in logs]


def get_all_logs_for_tank(tank_id: int, db: Session, skip: int = 0, limit: int = 10) -> list[WaterLogRead]:
    _get_tank_or_404(tank_id, db)
    logs = db.exec(
        select(WaterLog).where(WaterLog.tank_id == tank_id).offset(skip).limit(limit)
    ).all()
    return [evaluate_water_log(log) for log in logs]


def get_log(tank_id: int, log_id: int, db: Session) -> WaterLogRead:
    log = db.get(WaterLog, log_id)
    if not log or log.tank_id != tank_id:
        raise HTTPException(status_code=404, detail="Water log not found for this tank")
    return evaluate_water_log(log)


def update_log(tank_id: int, log_id: int, log_data: CreateWaterLog, db: Session) -> WaterLogRead:
    log = db.get(WaterLog, log_id)
    if not log or log.tank_id != tank_id:
        raise HTTPException(status_code=404, detail="Water log not found for this tank")

    log.sqlmodel_update(log_data.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(log)
    return evaluate_water_log(log)


def delete_log(tank_id: int, log_id: int, db: Session):
    log = db.get(WaterLog, log_id)
    if not log or log.tank_id != tank_id:
        raise HTTPException(status_code=404, detail="Water log not found for this tank")
    db.delete(log)
    db.commit()
    return {"message": "Water log deleted successfully"}
