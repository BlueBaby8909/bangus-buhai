from sqlmodel import Session, select

from models.water_log import WaterLog
from models.feeding_log import FeedingLog
from services.tank_services import view_tank
from services.water_quality import evaluate_water_log


def get_tank_summary(tank_id: int, db: Session) -> dict:
    tank = view_tank(tank_id=tank_id, db=db)

    latest_log = db.exec(
        select(WaterLog).where(WaterLog.tank_id == tank_id).order_by(WaterLog.recorded_at.desc())
    ).first()
    latest_feeding = db.exec(
        select(FeedingLog).where(FeedingLog.tank_id == tank_id).order_by(FeedingLog.fed_at.desc())
    ).first()

    total_logs = len(db.exec(select(WaterLog).where(WaterLog.tank_id == tank_id)).all())
    total_feedings = len(db.exec(select(FeedingLog).where(FeedingLog.tank_id == tank_id)).all())

    return {
        "tank": tank,
        "latest_water_log": evaluate_water_log(latest_log) if latest_log else None,
        "latest_feeding": latest_feeding,
        "total_water_logs": total_logs,
        "total_feedings": total_feedings,
    }
