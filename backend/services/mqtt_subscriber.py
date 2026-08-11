import asyncio
import json
import logging
from datetime import datetime, timezone

import aiomqtt
from sqlmodel import Session, select

from config import settings
from database.db import engine
from models.device import Device
from models.water_log import WaterLog
from services.websocket_manager import ws_manager
from services.water_quality import evaluate_water_log

logger = logging.getLogger("mqtt_subscriber")

class MQTTSubscriber:
    def __init__(self):
        self.topic_telemetry = f"{settings.mqtt_topic_prefix}/devices/+/telemetry"
        self.topic_status = f"{settings.mqtt_topic_prefix}/devices/+/status"
        # The command topic won't be subscribed here, but we will publish to it if needed later.

    async def handle_status(self, device_id: str, payload: dict):
        status = payload.get("status")
        with Session(engine) as db:
            device = db.exec(select(Device).where(Device.device_id == device_id)).first()
            if not device:
                device = Device(device_id=device_id)
                db.add(device)
            
            device.is_online = (status == "online")
            device.last_seen = datetime.now(timezone.utc)
            db.commit()
            
            # Broadcast device status update
            await ws_manager.broadcast_device_status(device_id, device.is_online)

    async def handle_telemetry(self, device_id: str, payload: dict):
        tank_id = payload.get("tank_id")
        fw_version = payload.get("fw_version")
        readings = payload.get("readings", {})
        
        with Session(engine) as db:
            # Upsert device
            device = db.exec(select(Device).where(Device.device_id == device_id)).first()
            if not device:
                device = Device(device_id=device_id)
                db.add(device)
            
            device.tank_id = tank_id
            device.firmware_version = fw_version
            device.is_online = True
            device.last_seen = datetime.now(timezone.utc)
            
            # Save water log
            water_log = WaterLog(
                tank_id=tank_id,
                device_id=device_id,
                temperature=readings.get("temperature", 0),
                pH=readings.get("ph", settings.ph_default),
                turbidity=readings.get("turbidity", 0),
                ph_source=readings.get("ph_source", "default"),
                relay_on=readings.get("relay_on", False),
                recorded_at=datetime.now(timezone.utc)
            )
            
            db.add(water_log)
            db.commit()
            db.refresh(water_log)
            
            # Evaluate water quality for warnings/status
            water_log_read = evaluate_water_log(water_log)

            # Broadcast telemetry to web clients
            await ws_manager.broadcast(
                tank_id, 
                {"type": "new_reading", "water_log": water_log_read.model_dump(mode="json")}
            )

    async def run(self):
        # aiomqtt Client automatically handles reconnections
        async with aiomqtt.Client(
            hostname=settings.mqtt_broker_host,
            port=settings.mqtt_broker_port,
            username=settings.mqtt_username or None,
            password=settings.mqtt_password or None,
            # tls_context=... (configured in Priority 3)
        ) as client:
            logger.info(f"Connected to MQTT broker at {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
            
            await client.subscribe(self.topic_telemetry)
            await client.subscribe(self.topic_status)
            
            async for message in client.messages:
                topic = str(message.topic)
                try:
                    payload = json.loads(message.payload.decode())
                    # Extract device_id from topic (e.g. bangusbuhai/devices/BB-123/telemetry)
                    parts = topic.split('/')
                    if len(parts) >= 3:
                        device_id = parts[2]
                        if topic.endswith("status"):
                            await self.handle_status(device_id, payload)
                        elif topic.endswith("telemetry"):
                            await self.handle_telemetry(device_id, payload)
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")

mqtt_subscriber = MQTTSubscriber()
