"""
Water quality evaluation for bangus (milkfish) grow-out tanks/ponds.

Thresholds are based on commonly cited milkfish culture guidelines:
  - Temperature: optimal 26-32 C
  - pH:          optimal 7.5-8.5, tolerable 6.5-9.0
  - Turbidity:   optimal <= 50 NTU, tolerable <= 100 NTU

These are reasonable general-purpose defaults, not a substitute for
site-specific advice from an aquaculture extension officer.
"""

from models.water_log import WaterLog, WaterLogRead

TEMP_OPTIMAL = (26.0, 32.0)
PH_OPTIMAL = (7.5, 8.5)
PH_TOLERABLE = (6.5, 9.0)
TURBIDITY_OPTIMAL_MAX = 50.0
TURBIDITY_TOLERABLE_MAX = 100.0


def evaluate_water_log(log: WaterLog) -> WaterLogRead:
    warnings: list[str] = []
    critical = False

    if log.temperature < TEMP_OPTIMAL[0] or log.temperature > TEMP_OPTIMAL[1]:
        warnings.append(
            f"Temperature {log.temperature}\u00b0C is outside the optimal "
            f"{TEMP_OPTIMAL[0]}-{TEMP_OPTIMAL[1]}\u00b0C range."
        )

    if log.pH < PH_TOLERABLE[0] or log.pH > PH_TOLERABLE[1]:
        warnings.append(f"pH {log.pH} is outside the safe range and needs immediate attention.")
        critical = True
    elif log.pH < PH_OPTIMAL[0] or log.pH > PH_OPTIMAL[1]:
        warnings.append(f"pH {log.pH} is outside the optimal {PH_OPTIMAL[0]}-{PH_OPTIMAL[1]} range.")

    if log.turbidity > TURBIDITY_TOLERABLE_MAX:
        warnings.append(f"Turbidity {log.turbidity} NTU is critically high.")
        critical = True
    elif log.turbidity > TURBIDITY_OPTIMAL_MAX:
        warnings.append(f"Turbidity {log.turbidity} NTU is above the optimal max of {TURBIDITY_OPTIMAL_MAX} NTU.")

    if critical:
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "optimal"

    return WaterLogRead(
        id=log.id,
        tank_id=log.tank_id,
        temperature=log.temperature,
        pH=log.pH,
        turbidity=log.turbidity,
        notes=log.notes,
        recorded_at=log.recorded_at,
        status=status,
        warnings=warnings,
    )
