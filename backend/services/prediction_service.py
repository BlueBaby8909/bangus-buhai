from fastapi import HTTPException
from sqlmodel import Session, select
from datetime import timedelta, timezone, datetime

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

    # Calculate confidence score
    # Apply a 20% penalty if any of the historical logs used a default/estimated pH
    # rather than a real sensor reading.
    confidence = 1.0
    if any(log.ph_source != "sensor" for log in logs):
        confidence = 0.8

    predictions_dict = predict(logs)

    prediction_db = Prediction(
        tank_id=tank_id,
        temperature_1h=predictions_dict["hour_1"]["temperature"],
        pH_1h=predictions_dict["hour_1"]["pH"],
        turbidity_1h=predictions_dict["hour_1"]["turbidity"],
        
        temperature_2h=predictions_dict["hour_2"]["temperature"],
        pH_2h=predictions_dict["hour_2"]["pH"],
        turbidity_2h=predictions_dict["hour_2"]["turbidity"],
        
        temperature_3h=predictions_dict["hour_3"]["temperature"],
        pH_3h=predictions_dict["hour_3"]["pH"],
        turbidity_3h=predictions_dict["hour_3"]["turbidity"],
        
        temperature_4h=predictions_dict["hour_4"]["temperature"],
        pH_4h=predictions_dict["hour_4"]["pH"],
        turbidity_4h=predictions_dict["hour_4"]["turbidity"],

        predicted_from=logs[-1].recorded_at,
        confidence_score=confidence,
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