from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Models must be imported before create_db_and_tables() runs so that
# SQLModel.metadata knows about every table.
from models.tank_profile import TankProfile
from models.user_profile import User
from models.water_log import WaterLog
from models.feeding_log import FeedingLog
from models.prediction import Prediction

from routes.tank_routes import router as tank_router
from routes.user_routes import router as user_router
from routes.waterlog_routes import router as water_log_router
from routes.feeding_routes import router as feeding_router

from database.db import create_db_and_tables
from config import settings

from ml.inference import load_resources
from routes.prediction_routes import router as prediction_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()

    load_resources()

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tank_router, prefix="/tanks", tags=["Tanks"])
app.include_router(water_log_router, prefix="/tanks", tags=["Water Logs"])
app.include_router(feeding_router, prefix="/tanks", tags=["Feeding Logs"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(prediction_router, prefix="/tanks/{tank_id}/predictions", tags=["Predictions"])
@app.get("/")
def root():
    return {"message": "BANGUS BUHAI"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}