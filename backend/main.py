"""
Bangus Buhai — FastAPI application entry point.

Lifespan sequence:
  1. create_db_and_tables() — ensure all SQLModel tables exist
  2. load_resources()       — load LSTM model + scaler into memory
  3. mqtt_task             — start MQTT subscriber as background asyncio task

The MQTT subscriber is the bridge between the ESP32 device and the database.
It subscribes to:
  bangusbuhai/devices/+/telemetry
  bangusbuhai/devices/+/status

And for each telemetry message: writes a WaterLog row, evaluates water quality,
and pushes real-time updates to connected WebSocket clients.
"""

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Models must be imported before create_db_and_tables() so SQLModel.metadata
# knows about every table.
from models.tank_profile import TankProfile
from models.water_log import WaterLog
from models.prediction import Prediction
from models.device import Device

from routes.tank_routes import router as tank_router
from routes.waterlog_routes import router as water_log_router
from routes.prediction_routes import router as prediction_router
from routes.device_routes import router as device_router
from routes.websocket_routes import router as ws_router

from database.db import create_db_and_tables
from config import settings
from ml.inference import load_resources
from services.mqtt_subscriber import mqtt_subscriber

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    logger.info("Database tables ready")

    load_resources()
    logger.info("ML model loaded")

    # Start MQTT subscriber as a background task
    mqtt_task = asyncio.create_task(mqtt_subscriber.run(), name="mqtt_subscriber")
    logger.info("MQTT subscriber started")

    yield  # Application runs here

    # Shutdown
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        logger.info("MQTT subscriber stopped cleanly")


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

# REST routes
app.include_router(tank_router,       prefix="/tanks",   tags=["Tanks"])
app.include_router(water_log_router,  prefix="/tanks",   tags=["Water Logs"])
app.include_router(prediction_router, prefix="/tanks/{tank_id}/predictions", tags=["Predictions"])
app.include_router(device_router,                        tags=["Devices"])

# WebSocket routes (no prefix — path is /ws/tanks/{tank_id})
app.include_router(ws_router)


@app.get("/")
def root():
    return {"message": "Bangus Buhai API", "version": settings.app_version}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}