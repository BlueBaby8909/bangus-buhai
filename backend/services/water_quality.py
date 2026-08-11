"""
Water quality evaluation for bangus (milkfish) grow-out ponds.

Thresholds are based on commonly cited milkfish culture guidelines:
  Temperature: optimal 26–32°C
  pH:          optimal 7.5–8.5, tolerable 6.5–9.0
  Turbidity:   optimal ≤ 50 NTU, tolerable ≤ 100 NTU

NOTE ON pH:
  The current prototype does not have a pH sensor. The ph_source field
  indicates where the pH value came from:
    "sensor"  — real measurement (future hardware)
    "default" — firmware constant (7.80), not a real measurement
    "manual"  — entered by the user via the app

  ph_is_estimated is set True when ph_source != "sensor".
  The frontend uses this to show a ⚠ badge next to the pH reading.
  pH threshold warnings are still computed — they're just labelled as
  estimated in the response.
"""

from models.water_log import WaterLog, WaterLogRead

TEMP_OPTIMAL   = (26.0, 32.0)
PH_OPTIMAL     = (7.5, 8.5)
PH_TOLERABLE   = (6.5, 9.0)
TURB_OPTIMAL_MAX   = 50.0
TURB_TOLERABLE_MAX = 100.0


def evaluate_water_log(log: WaterLog) -> WaterLogRead:
    """
    Evaluate a water log against milkfish culture thresholds.

    Returns a WaterLogRead with:
      - status:          "optimal" | "warning" | "critical"
      - warnings:        list of human-readable warning strings
      - ph_is_estimated: True when pH did not come from a physical sensor
    """
    warnings: list[str] = []
    critical = False

    # Temperature
    if log.temperature < TEMP_OPTIMAL[0] or log.temperature > TEMP_OPTIMAL[1]:
        warnings.append(
            f"Temperature {log.temperature:.1f}°C is outside the optimal "
            f"{TEMP_OPTIMAL[0]}–{TEMP_OPTIMAL[1]}°C range."
        )

    # pH (labelled if estimated)
    ph_label = " (estimated)" if log.ph_source != "sensor" else ""

    if log.pH < PH_TOLERABLE[0] or log.pH > PH_TOLERABLE[1]:
        warnings.append(
            f"pH {log.pH:.2f}{ph_label} is critically outside the safe range "
            f"{PH_TOLERABLE[0]}–{PH_TOLERABLE[1]} and needs immediate attention."
        )
        critical = True
    elif log.pH < PH_OPTIMAL[0] or log.pH > PH_OPTIMAL[1]:
        warnings.append(
            f"pH {log.pH:.2f}{ph_label} is outside the optimal "
            f"{PH_OPTIMAL[0]}–{PH_OPTIMAL[1]} range."
        )

    # Turbidity
    if log.turbidity > TURB_TOLERABLE_MAX:
        warnings.append(
            f"Turbidity {log.turbidity:.1f} NTU is critically high."
        )
        critical = True
    elif log.turbidity > TURB_OPTIMAL_MAX:
        warnings.append(
            f"Turbidity {log.turbidity:.1f} NTU is above the optimal "
            f"maximum of {TURB_OPTIMAL_MAX:.0f} NTU."
        )

    if critical:
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "optimal"

    return WaterLogRead(
        id              = log.id,
        tank_id         = log.tank_id,
        temperature     = log.temperature,
        pH              = log.pH,
        turbidity       = log.turbidity,
        ph_source       = log.ph_source,
        relay_on        = log.relay_on,
        notes           = log.notes,
        recorded_at     = log.recorded_at,
        status          = status,
        warnings        = warnings,
        ph_is_estimated = log.ph_source != "sensor",
    )
