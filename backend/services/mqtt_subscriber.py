import asyncio
import json
import logging
from datetime import datetime, timezone
import ssl

import paho.mqtt.client as mqtt
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
        self.client = None
        self.main_loop = None

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
            
            await ws_manager.broadcast_device_status(device_id, device.is_online)

    async def handle_telemetry(self, device_id: str, payload: dict):
        tank_id = payload.get("tank_id")
        fw_version = payload.get("fw_version")
        readings = payload.get("readings", {})
        
        with Session(engine) as db:
            device = db.exec(select(Device).where(Device.device_id == device_id)).first()
            if not device:
                device = Device(device_id=device_id)
                db.add(device)
            
            device.tank_id = tank_id
            device.firmware_version = fw_version
            device.is_online = True
            device.last_seen = datetime.now(timezone.utc)
            
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
            
            water_log_read = evaluate_water_log(water_log)

            await ws_manager.broadcast(
                tank_id, 
                {"type": "new_reading", "water_log": water_log_read.model_dump(mode="json")}
            )

            from services.prediction_service import create_prediction
            from fastapi import HTTPException
            try:
                pred_read = create_prediction(tank_id, db)
                await ws_manager.broadcast(
                    tank_id,
                    {"type": "new_prediction", "prediction": pred_read.model_dump(mode="json")}
                )
            except HTTPException:
                pass
            except Exception as e:
                logger.error(f"Error generating prediction for tank {tank_id}: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
            client.subscribe(self.topic_telemetry)
            client.subscribe(self.topic_status)
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            parts = topic.split('/')
            if len(parts) >= 3:
                device_id = parts[2]
                if topic.endswith("status") and self.main_loop:
                    asyncio.run_coroutine_threadsafe(self.handle_status(device_id, payload), self.main_loop)
                elif topic.endswith("telemetry") and self.main_loop:
                    asyncio.run_coroutine_threadsafe(self.handle_telemetry(device_id, payload), self.main_loop)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def start(self):
        self.main_loop = asyncio.get_running_loop()
        
        try:
            from paho.mqtt.enums import CallbackAPIVersion
            self.client = mqtt.Client(CallbackAPIVersion.VERSION1)
        except ImportError:
            self.client = mqtt.Client()

        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        if settings.mqtt_use_tls:
            tls_context = ssl.create_default_context()
            self.client.tls_set_context(tls_context)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
            self.client.loop_start() 
        except Exception as e:
            logger.error(f"Could not connect to MQTT Broker: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    async def publish_relay_command(self, device_id: str, relay_on: bool):
        topic = f"{settings.mqtt_topic_prefix}/devices/{device_id}/cmd"
        payload = json.dumps({"relay": "heater", "state": relay_on})
        try:
            if self.client:
                self.client.publish(topic, payload, qos=1)
                logger.info(f"Published relay command to {topic}: {payload}")
            else:
                logger.error(f"Cannot publish, MQTT client is not connected.")
        except Exception as e:
            logger.error(f"Failed to publish relay command to {device_id}: {e}")
            raise e

mqtt_subscriber = MQTTSubscriber()
