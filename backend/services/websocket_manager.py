"""
WebSocket connection manager for real-time frontend updates.

When the MQTT subscriber receives new telemetry, it calls ws_manager.broadcast()
to push the data to all WebSocket clients currently viewing that tank's dashboard.
This is what makes the frontend update live without polling.

Why WebSocket (not Server-Sent Events)?
  Both work. WebSocket is bidirectional (could support future commands from the
  UI to the device). SSE is simpler for one-way streaming. We use WebSocket here
  for flexibility — the frontend only receives in practice, but the protocol
  supports future use cases like "trigger manual relay" from the dashboard.
"""

import asyncio
import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    pass

logger = logging.getLogger("ws_manager")


class WebSocketManager:
    """
    Manages active WebSocket connections grouped by tank_id.

    Clients connect to /ws/tanks/{tank_id} and receive JSON messages whenever:
      - A new water log is created for that tank (type: "new_reading")
      - The device for that tank changes online/offline status (type: "device_status")
    """

    def __init__(self):
        # {tank_id: set of connected WebSocket objects}
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        # {device_id: tank_id} reverse map for device status broadcasts
        self._device_tank_map: dict[str, int] = {}

    async def connect(self, websocket: WebSocket, tank_id: int):
        await websocket.accept()
        self._connections[tank_id].add(websocket)
        logger.info("WebSocket connected for tank %d (total: %d)",
                    tank_id, len(self._connections[tank_id]))

    def disconnect(self, websocket: WebSocket, tank_id: int):
        self._connections[tank_id].discard(websocket)
        if not self._connections[tank_id]:
            del self._connections[tank_id]
        logger.info("WebSocket disconnected from tank %d", tank_id)

    async def broadcast(self, tank_id: int, data: dict):
        """Send a JSON message to all clients watching tank_id."""
        clients = self._connections.get(tank_id)
        if not clients:
            return

        message = json.dumps(data)
        disconnected = set()

        for ws in clients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.disconnect(ws, tank_id)

    async def broadcast_device_status(self, device_id: str, is_online: bool):
        """Broadcast device status change to the tank this device belongs to."""
        tank_id = self._device_tank_map.get(device_id)
        if tank_id is None:
            return

        await self.broadcast(tank_id, {
            "type": "device_status",
            "device_id": device_id,
            "is_online": is_online,
        })

    def register_device(self, device_id: str, tank_id: int):
        self._device_tank_map[device_id] = tank_id


# Module-level singleton
ws_manager = WebSocketManager()
