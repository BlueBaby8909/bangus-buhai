import asyncio
import json
import random
import time
from datetime import datetime

import aiomqtt
import sys

# Fix for Windows asyncio loop with aiomqtt
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import sys

# Configuration matching your backend/mosquitto setup
BROKER_HOST = "localhost"
BROKER_PORT = 1883
BROKER_USERNAME = "bangus_backend"
BROKER_PASSWORD = "bangusbuhai123"
TOPIC_PREFIX = "bangusbuhai"
DEVICE_ID = "BB-MOCK-123456"

# Get Tank ID from command line argument, or default to 1
try:
    TANK_ID = int(sys.argv[1])
except IndexError:
    TANK_ID = 1


async def main():
    print(f"Connecting to mock MQTT broker at {BROKER_HOST}:{BROKER_PORT}...")
    
    async with aiomqtt.Client(
        hostname=BROKER_HOST, 
        port=BROKER_PORT,
        username=BROKER_USERNAME,
        password=BROKER_PASSWORD
    ) as client:
        print("Connected! Sending device online status...")
        
        # 1. Send Online Status
        await client.publish(
            f"{TOPIC_PREFIX}/devices/{DEVICE_ID}/status",
            payload=json.dumps({"device_id": DEVICE_ID, "status": "online"}),
            qos=1
        )
        
        # 2. Subscribe to commands
        command_topic = f"{TOPIC_PREFIX}/devices/{DEVICE_ID}/command"
        await client.subscribe(command_topic)
        print(f"Subscribed to commands at {command_topic}")
        
        print(f"Starting telemetry loop for Tank {TANK_ID} (Device: {DEVICE_ID})")
        print("Press Ctrl+C to stop.\n")
        
        seq = 0
        current_relay_state = False
        
        async def listen_for_commands():
            nonlocal current_relay_state
            async for message in client.messages:
                if str(message.topic) == command_topic:
                    cmd = json.loads(message.payload.decode())
                    print(f"\n[DEVICE RECEIVED COMMAND] -> {cmd}\n")
                    if cmd.get("relay") == "heater":
                        current_relay_state = cmd.get("state", False)

        # Start the listener task in the background
        asyncio.create_task(listen_for_commands())
        
        try:
            while True:
                # Generate realistic-looking mock data
                temp = round(random.uniform(28.0, 33.5), 1)
                turbidity = round(random.uniform(5.0, 50.0), 1)
                
                payload = {
                    "device_id": DEVICE_ID,
                    "tank_id": TANK_ID,
                    "seq": seq,
                    "fw_version": "1.0.0-mock",
                    "uptime_s": seq * 10,
                    "readings": {
                        "temperature": temp,
                        "turbidity": turbidity,
                        "ph": 7.80,
                        "ph_source": "default",
                        "relay_on": current_relay_state
                    },
                    "system": {
                        "free_heap": 150000,
                        "wifi_rssi": -55,
                        "mqtt_reconnects": 0
                    }
                }
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending telemetry: Temp={temp}°C, Turbidity={turbidity} NTU")
                
                await client.publish(
                    f"{TOPIC_PREFIX}/devices/{DEVICE_ID}/telemetry",
                    payload=json.dumps(payload),
                    qos=1
                )
                
                seq += 1
                await asyncio.sleep(5)  # Send data every 5 seconds for fast testing
                
        except asyncio.CancelledError:
            pass
        finally:
            print("\nSending device offline status...")
            await client.publish(
                f"{TOPIC_PREFIX}/devices/{DEVICE_ID}/status",
                payload=json.dumps({"device_id": DEVICE_ID, "status": "offline"}),
                qos=1
            )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Mock device stopped.")
