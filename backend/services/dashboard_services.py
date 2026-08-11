from sqlmodel import Session, select, func

from models.water_log import WaterLog
from services.tank_services import view_tank
from services.water_quality import evaluate_water_log


def get_tank_summary(tank_id: int, db: Session) -> dict:
    tank = view_tank(tank_id=tank_id, db=db)

    latest_log = db.exec(
        select(WaterLog).where(WaterLog.tank_id == tank_id).order_by(WaterLog.recorded_at.desc())
    ).first()

    total_logs = db.exec(select(func.count(WaterLog.id)).where(WaterLog.tank_id == tank_id)).one()

    return {
        "tank": tank,
        "latest_water_log": evaluate_water_log(latest_log) if latest_log else None,
        "total_water_logs": total_logs,
    }
