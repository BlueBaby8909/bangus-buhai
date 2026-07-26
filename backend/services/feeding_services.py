from fastapi import HTTPException
from models.feeding_log import CreateFeedingLog, FeedingLog
from models.tank_profile import TankProfile
from sqlmodel import Session, select


def _get_tank_or_404(tank_id: int, db: Session) -> TankProfile:
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return tank


def create_feeding_log(tank_id: int, feeding: CreateFeedingLog, db: Session) -> FeedingLog:
    _get_tank_or_404(tank_id, db)

    db_feeding = FeedingLog.model_validate(feeding, update={"tank_id": tank_id})
    db.add(db_feeding)
    db.commit()
    db.refresh(db_feeding)
    return db_feeding


def get_all_feeding_logs_for_tank(tank_id: int, db: Session, skip: int = 0, limit: int = 10):
    _get_tank_or_404(tank_id, db)
    return db.exec(
        select(FeedingLog).where(FeedingLog.tank_id == tank_id).offset(skip).limit(limit)
    ).all()


def get_feeding_log(tank_id: int, feeding_id: int, db: Session) -> FeedingLog:
    feeding = db.get(FeedingLog, feeding_id)
    if not feeding or feeding.tank_id != tank_id:
        raise HTTPException(status_code=404, detail="Feeding log not found for this tank")
    return feeding


def delete_feeding_log(tank_id: int, feeding_id: int, db: Session):
    feeding = db.get(FeedingLog, feeding_id)
    if not feeding or feeding.tank_id != tank_id:
        raise HTTPException(status_code=404, detail="Feeding log not found for this tank")
    db.delete(feeding)
    db.commit()
    return {"message": "Feeding log deleted successfully"}
