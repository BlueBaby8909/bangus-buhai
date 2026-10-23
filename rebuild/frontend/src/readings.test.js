import { describe, it, expect } from "vitest";
import { metric, mergeReading, chartRows, display } from "./readings";
const device = {
  origin: "device",
  id: "a",
  device_id: "BB-1",
  measured_at: "2026-10-22T00:00:00Z",
  received_at: "2026-10-22T00:00:01Z",
  telemetry: {
    readings: {
      temperature: {
        value: 28,
        validity: "valid",
        source: "sensor",
        sample_age_ms: 1000,
      },
      ph: {
        value: 7,
        validity: "unverified",
        source: "default",
        sample_age_ms: null,
      },
      turbidity: {
        value: null,
        validity: "missing",
        source: "sensor",
        sample_age_ms: null,
      },
    },
  },
};
describe("truthful readings", () => {
  it("does not convert missing data into zero", () => {
    expect(display(null)).toBe("—");
    expect(display(0)).toBe("0");
    expect(metric(null, "temperature").value).toBeNull();
  });
  it("retains default pH and stales temperature at the existing boundary", () => {
    expect(metric(device, "ph").label).toBe("Default · unverified");
    expect(
      metric(device, "temperature", Date.parse(device.measured_at) + 58999)
        .label,
    ).toBe("valid");
    expect(
      metric(device, "temperature", Date.parse(device.measured_at) + 59000)
        .label,
    ).toBe("Stale");
  });
  it("keeps missing/invalid validity even when time is uncertain", () => {
    const r = { ...device, measured_at: null };
    expect(metric(r, "temperature").label).toBe("Capture time uncertain");
    expect(metric(r, "turbidity").label).toBe("missing");
  });
  it("does not regress manual versions or duplicate captures", () => {
    const first = {
      origin: "manual",
      id: "m",
      version: 1,
      received_at: device.received_at,
    };
    const next = { ...first, version: 2, voided: true };
    expect(mergeReading([next], first)).toEqual([next]);
    expect(mergeReading([first], next)).toEqual([next]);
    expect(mergeReading([device], device)).toEqual([device]);
  });
  it("separates sources and drops void/unknown timestamps", () => {
    const manual = {
      origin: "manual",
      id: "m",
      version: 1,
      measured_at: device.measured_at,
      received_at: device.received_at,
      temperature_c: 27,
    };
    const data = chartRows(
      [
        device,
        { ...device, id: "b", device_id: "BB-2" },
        manual,
        { ...manual, id: "x", voided: true },
        { ...device, id: "u", measured_at: null },
      ],
      "BB-1",
      "temperature",
    );
    expect(data).toHaveLength(2);
    expect(data[0].device).toBe(28);
    expect(data[1].manual).toBe(27);
  });
});
