from models.water_log import WaterLog
from models.prediction import Prediction

from fastapi import HTTPException
from models.tank_profile import CreateTankProfile, TankProfile
from sqlmodel import Session, select, delete

# Capacity is derived, not user-supplied: 1 mL of water is treated as
# supporting roughly 1/600th of a gram of fish biomass at safe stocking density.
ML_TO_CAPACITY_FACTOR = 600


def _compute_capacity(volume_ml: float) -> float:
    return volume_ml * ML_TO_CAPACITY_FACTOR


# create tank profile
def create_tank(tank_profile: CreateTankProfile, db: Session):
    db_tank = TankProfile.model_validate(tank_profile)
    db_tank.capacity = _compute_capacity(tank_profile.volume_ml)

    db.add(db_tank)
    db.commit()
    db.refresh(db_tank)
    return db_tank


# get all tanks
def get_all_tanks(db: Session, skip: int = 0, limit: int = 10):
    query = select(TankProfile)
    tanks = db.exec(query.offset(skip).limit(limit)).all()
    return tanks


# specific one tank only
def view_tank(tank_id: int, db: Session):
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return tank


# update one tank
def update_tank(tank_id: int, tank_data: CreateTankProfile, db: Session):
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    tank.sqlmodel_update(tank_data.model_dump(exclude_unset=True))
    tank.capacity = _compute_capacity(tank.volume_ml)

    db.commit()
    db.refresh(tank)
    return tank

def delete_tank(tank_id: int, db: Session):
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    # Bulk DELETE — one query per related table instead of N queries.
    # Previously used `for log in logs: db.delete(log)` which executes
    # one DELETE per row and hangs on tanks with thousands of logs.
    db.exec(delete(WaterLog).where(WaterLog.tank_id == tank_id))
    db.exec(delete(Prediction).where(Prediction.tank_id == tank_id))

    db.delete(tank)
    db.commit()
    return {"message": "Tank deleted successfully!"}
