"""
WebSocket routes for real-time tank updates.

Frontend connects to /ws/tanks/{tank_id} and receives JSON messages pushed
by the MQTT subscriber whenever new sensor data arrives.

Message format — new reading:
{
  "type": "new_reading",
  "water_log": { ...WaterLogRead fields... }
}

Message format — device status:
{
  "type": "device_status",
  "device_id": "BB-AABBCC112233",
  "is_online": true
}
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_manager import ws_manager

logger = logging.getLogger("ws_routes")

router = APIRouter()


@router.websocket("/ws/tanks/{tank_id}")
async def tank_websocket(websocket: WebSocket, tank_id: int):
    """
    WebSocket endpoint for real-time updates on a specific tank.

    The frontend connects here and keeps the connection open.
    When a new water log arrives (via MQTT), it is pushed to all connected
    clients for that tank without any polling.
    """
    await ws_manager.connect(websocket, tank_id)
    logger.info("WebSocket client connected to tank %d", tank_id)

    try:
        # Keep the connection alive by waiting for any client message.
        # (Clients don't need to send anything — this just detects disconnects.)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, tank_id)
        logger.info("WebSocket client disconnected from tank %d", tank_id)
