from fastapi import HTTPException
from sqlmodel import Session, select
from datetime import timedelta

from models.water_log import WaterLog
from models.tank_profile import TankProfile
from models.prediction import Prediction, PredictionRead
from ml.inference import predict, SEQ_LENGTH


def _get_tank_or_404(tank_id: int, db: Session) -> TankProfile:
    tank = db.get(TankProfile, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return tank


def create_prediction(tank_id: int, db: Session) -> PredictionRead:
    """
    Predict the next water quality values for a tank
    using the latest SEQ_LENGTH water logs.
    """

    _get_tank_or_404(tank_id, db)

    logs = db.exec(
        select(WaterLog)
        .where(WaterLog.tank_id == tank_id)
        .order_by(WaterLog.recorded_at.desc())
        .limit(SEQ_LENGTH)
    ).all()

    if len(logs) < SEQ_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"At least {SEQ_LENGTH} water logs are required for prediction."
        )

    # Reverse because the query returns newest -> oldest, but the model
    # expects the sequence in chronological (oldest -> newest) order.
    logs.reverse()

    prediction = predict(logs)

    prediction_db = Prediction(
        tank_id=tank_id,
        temperature=prediction["temperature"],
        pH=prediction["pH"],
        turbidity=prediction["turbidity"],
        predicted_for=logs[-1].recorded_at + timedelta(hours=3),
    )

    db.add(prediction_db)
    db.commit()
    db.refresh(prediction_db)

    return PredictionRead.model_validate(prediction_db)


def get_prediction_history(tank_id: int, db: Session) -> list[PredictionRead]:
    """
    Return all saved predictions for a tank, most recent first.
    """

    _get_tank_or_404(tank_id, db)

    predictions = db.exec(
        select(Prediction)
        .where(Prediction.tank_id == tank_id)
        .order_by(Prediction.created_at.desc())
    ).all()

    return [PredictionRead.model_validate(p) for p in predictions]


def get_latest_prediction(tank_id: int, db: Session) -> PredictionRead:
    """
    Return the most recently created prediction for a tank.
    """

    _get_tank_or_404(tank_id, db)

    prediction = db.exec(
        select(Prediction)
        .where(Prediction.tank_id == tank_id)
        .order_by(Prediction.created_at.desc())
    ).first()

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="No predictions found for this tank."
        )

    return PredictionRead.model_validate(prediction)