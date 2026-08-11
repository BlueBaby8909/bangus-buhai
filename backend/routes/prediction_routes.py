from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from database.db import get_session
from models.prediction import PredictionRead
import services.prediction_service as service

router = APIRouter()


@router.post(
    "/",
    response_model=PredictionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_prediction(
    tank_id: int,
    db: Session = Depends(get_session),
):
    """
    Generate and save a new prediction using the latest
    48 water logs of the specified tank.
    """
    return service.create_prediction(
        tank_id=tank_id,
        db=db,
    )


@router.get(
    "/",
    response_model=list[PredictionRead],
    status_code=status.HTTP_200_OK,
)
def get_prediction_history(
    tank_id: int,
    db: Session = Depends(get_session),
):
    """
    Return all predictions for the specified tank.
    """
    return service.get_prediction_history(
        tank_id=tank_id,
        db=db,
    )


@router.get(
    "/latest",
    response_model=PredictionRead,
    status_code=status.HTTP_200_OK,
)
def get_latest_prediction(
    tank_id: int,
    db: Session = Depends(get_session),
):
    """
    Return the latest prediction for the specified tank.
    """
    return service.get_latest_prediction(
        tank_id=tank_id,
        db=db,
    )