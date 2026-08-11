"""
Device management routes.
"""

import json
import aiomqtt
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database.db import get_session
from models.device import Device, DeviceRead
from config import settings

class CommandRequest(BaseModel):
    relay: str
    state: bool

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_session)):
    """List all registered devices."""
    return db.exec(select(Device)).all()


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: str, db: Session = Depends(get_session)):
    """Get a specific device by its ID string."""
    device = db.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/{device_id}/command", status_code=status.HTTP_202_ACCEPTED)
async def send_command(device_id: str, command: CommandRequest, db: Session = Depends(get_session)):
    """Send a command (e.g., relay toggle) to a specific device via MQTT."""
    # Ensure device exists
    device = db.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    topic = f"{settings.mqtt_topic_prefix}/devices/{device_id}/command"
    payload = json.dumps({"relay": command.relay, "state": command.state})

    try:
        async with aiomqtt.Client(
            hostname=settings.mqtt_broker_host,
            port=settings.mqtt_broker_port,
            username=settings.mqtt_username or None,
            password=settings.mqtt_password or None,
        ) as client:
            await client.publish(topic, payload, qos=1)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to publish MQTT message: {str(e)}"
        )
    
    return {"status": "Command sent", "topic": topic, "payload": payload}
