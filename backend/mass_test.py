import math
import requests

BASE_URL = "http://127.0.0.1:8000"


def check(response, expected_status, name):
    print(f"{name}: {response.status_code}", end="")

    if response.status_code != expected_status:
        print(" ❌")
        print(response.text)
        raise SystemExit(1)

    print(" ✅")


# ============================================================
# 1. CREATE TEST TANK
# ============================================================

tank_response = requests.post(
    f"{BASE_URL}/tanks/",
    json={
        "name": "ML MASS TEST TANK",
        "volume_ml": 100000,
        "growth_stage": "fry"
    }
)

check(tank_response, 201, "Create tank")

tank = tank_response.json()
tank_id = tank["id"]

print(f"Tank ID: {tank_id}")


# ============================================================
# 2. CREATE 47 LOGS
# ============================================================

print("\nCreating first 47 water logs...")

for i in range(47):

    temperature = 29.5 + 0.5 * math.sin(i / 8)
    ph = 7.7 + 0.05 * math.sin(i / 7)
    turbidity = 15 + 2 * math.sin(i / 6)

    response = requests.post(
        f"{BASE_URL}/tanks/{tank_id}/logs",
        json={
            "temperature": round(temperature, 3),
            "pH": round(ph, 3),
            "turbidity": round(turbidity, 3),
            "notes": f"ML mass test log {i + 1}"
        }
    )

    check(response, 201, f"Log {i + 1}/48")


# ============================================================
# 3. TRY PREDICTION WITH ONLY 47 LOGS
# ============================================================

print("\nTesting insufficient-log protection...")

response = requests.post(
    f"{BASE_URL}/tanks/{tank_id}/predictions/"
)

check(response, 400, "Prediction with 47 logs")

print("Correctly rejected prediction with fewer than 48 logs.")


# ============================================================
# 4. CREATE LOG #48
# ============================================================

print("\nCreating log 48...")

response = requests.post(
    f"{BASE_URL}/tanks/{tank_id}/logs",
    json={
        "temperature": 30.0,
        "pH": 7.75,
        "turbidity": 16.0,
        "notes": "ML mass test log 48"
    }
)

check(response, 201, "Log 48/48")


# ============================================================
# 5. RUN REAL ML PREDICTION
# ============================================================

print("\nRunning REAL LSTM prediction...")

response = requests.post(
    f"{BASE_URL}/tanks/{tank_id}/predictions/"
)

check(response, 201, "ML prediction")

prediction = response.json()

print("\nPrediction returned:")
print(f"  Temp 1h   : {prediction['temperature_1h']}")
print(f"  pH 1h     : {prediction['pH_1h']}")
print(f"  Turb 1h   : {prediction['turbidity_1h']}")
print(f"  Temp 4h   : {prediction['temperature_4h']}")
print(f"  Predicted From : {prediction['predicted_from']}")


# ============================================================
# 6. VERIFY PREDICTION HISTORY
# ============================================================

print("\nChecking prediction history...")

response = requests.get(
    f"{BASE_URL}/tanks/{tank_id}/predictions/"
)

check(response, 200, "Prediction history")

history = response.json()

print(f"Predictions stored: {len(history)}")

if len(history) < 1:
    print("❌ Prediction was not persisted.")
    raise SystemExit(1)

print("Prediction successfully saved to database. ✅")


# ============================================================
# 7. VERIFY LATEST PREDICTION
# ============================================================

print("\nChecking latest prediction...")

response = requests.get(
    f"{BASE_URL}/tanks/{tank_id}/predictions/latest"
)

check(response, 200, "Latest prediction")

latest = response.json()

print("\nLatest prediction:")
print(latest)


# ============================================================
# DONE
# ============================================================

print("\n" + "=" * 60)
print("ML MASS TEST PASSED ✅")
print("=" * 60)
print(f"Tank ID: {tank_id}")
print("Water logs: 48")
print("Insufficient logs test: PASSED")
print("LSTM prediction: PASSED")
print("Prediction persistence: PASSED")
print("Prediction history: PASSED")
print("Latest prediction: PASSED")