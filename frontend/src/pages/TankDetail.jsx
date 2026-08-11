import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import RangeGauge from "../components/RangeGauge";
import Modal from "../components/Modal";
import WaterLogForm from "../components/WaterLogForm";
import { THRESHOLDS, toneForMetric } from "../lib/waterQuality";
import { DeviceStatus } from "../components/DeviceStatus";
import { PhSourceBadge } from "../components/PhSourceBadge";
import { getWsUrl } from "../api/client";
import { PredictionCard } from "../components/PredictionCard";
import { WaterLogChart } from "../components/WaterLogChart";

export default function TankDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [waterLogs, setWaterLogs] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showWaterForm, setShowWaterForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  
  const [deviceState, setDeviceState] = useState({ isOnline: false, lastSeen: null, deviceId: null });

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.getTankSummary(id),
      api.listWaterLogs(id, { limit: 50 }),
      api.getLatestPrediction(id).catch(() => null),
    ])
      .then(([s, logs, pred]) => {
        setSummary(s);
        setWaterLogs(logs.slice().reverse());
        setPrediction(pred);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadAll();

    // Fetch initial device status
    api.listDevices().then(devices => {
      const device = devices.find(d => d.tank_id === parseInt(id));
      if (device) {
        setDeviceState({ isOnline: device.is_online, lastSeen: device.last_seen, deviceId: device.device_id });
      }
    }).catch(console.error);

    // Setup WebSocket with reconnection logic
    let ws;
    let reconnectTimer;

    const connectWs = () => {
      ws = new WebSocket(getWsUrl(`/ws/tanks/${id}`));
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "new_reading" && data.water_log) {
            setWaterLogs(prev => [data.water_log, ...prev]);
            setSummary(prev => prev ? { ...prev, latest_water_log: data.water_log, total_water_logs: prev.total_water_logs + 1 } : prev);
          } else if (data.type === "device_status") {
            setDeviceState(prev => ({ ...prev, isOnline: data.is_online }));
          }
        } catch (err) {
          console.error("WebSocket message parse error", err);
        }
      };

      ws.onclose = () => {
        console.warn("WebSocket disconnected. Reconnecting in 3s...");
        reconnectTimer = setTimeout(connectWs, 3000);
      };
    };

    connectWs();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null; // prevent reconnect on unmount
        ws.close();
      }
    };
  }, [loadAll, id]);

  const handleAddWaterLog = async (data) => {
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createWaterLog(id, data);
      setShowWaterForm(false);
      loadAll();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Could not save reading.");
    } finally {
      setSubmitting(false);
    }
  };


  const handleDeleteTank = async () => {
    if (!confirm(`Delete "${summary?.tank?.name}"? This cannot be undone.`)) return;
    await api.deleteTank(id);
    navigate("/");
  };

  const handleToggleHeater = async (e) => {
    const turnOn = e.target.checked;
    try {
      await api.sendCommand(deviceState.deviceId, { relay: "heater", state: turnOn });
    } catch (err) {
      alert("Failed to send command to device: " + err.message);
    }
  };

  if (loading) return <div className="loading-strip">Loading tank...</div>;
  if (error) return <div className="form-error">{error}</div>;

  const tank = summary?.tank;
  const latest = summary?.latest_water_log;

  return (
    <>
      <Link to="/" className="back-link">
        &larr; All tanks
      </Link>

      <div className="detail-header">
        <div>
          <div className="page-header__eyebrow">{tank.growth_stage}</div>
          <h1>{tank.name}</h1>
          <DeviceStatus 
            isOnline={deviceState.isOnline} 
            lastSeen={deviceState.lastSeen} 
            style={{ marginTop: "8px" }} 
          />
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
          <StatusBadge status={latest?.status || "unknown"} />
          <button className="btn btn-danger" onClick={handleDeleteTank}>
            Delete tank
          </button>
        </div>
      </div>

      <div className="summary-strip">
        <div className="summary-tile">
          <div className="summary-tile__label">Capacity</div>
          <div className="summary-tile__value mono">{tank.capacity.toLocaleString()}</div>
        </div>
        <div className="summary-tile">
          <div className="summary-tile__label">Water logs</div>
          <div className="summary-tile__value mono">{summary.total_water_logs}</div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h3 style={{ marginBottom: "8px" }}>Latest reading</h3>
          {latest ? (
            <>
              <RangeGauge
                label="Temp"
                value={latest.temperature}
                unit={THRESHOLDS.temperature.unit}
                min={THRESHOLDS.temperature.min}
                max={THRESHOLDS.temperature.max}
                optimalFrom={THRESHOLDS.temperature.optimalFrom}
                optimalTo={THRESHOLDS.temperature.optimalTo}
                tone={toneForMetric("temperature", latest.temperature)}
              />
              <div style={{ display: "flex", alignItems: "center" }}>
                <RangeGauge
                  label="pH"
                  value={latest.pH}
                  unit={THRESHOLDS.pH.unit}
                  min={THRESHOLDS.pH.min}
                  max={THRESHOLDS.pH.max}
                  optimalFrom={THRESHOLDS.pH.optimalFrom}
                  optimalTo={THRESHOLDS.pH.optimalTo}
                  tone={toneForMetric("pH", latest.pH)}
                />
                <PhSourceBadge isEstimated={latest.ph_is_estimated} />
              </div>
              <RangeGauge
                label="Turbidity"
                value={latest.turbidity}
                unit={THRESHOLDS.turbidity.unit}
                min={THRESHOLDS.turbidity.min}
                max={THRESHOLDS.turbidity.max}
                optimalFrom={THRESHOLDS.turbidity.optimalFrom}
                optimalTo={THRESHOLDS.turbidity.optimalTo}
                tone={toneForMetric("turbidity", latest.turbidity)}
              />
              {latest.warnings?.length > 0 && (
                <div className="log-row__warnings">
                  {latest.warnings.map((w, i) => (
                    <div key={i}>&bull; {w}</div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p style={{ color: "var(--ink-soft)" }}>No readings logged yet.</p>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: "16px" }}>Manual Controls</h3>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div className="font-medium text-gray-800">Heater Relay</div>
              <div className="text-sm text-gray-500">Override thermostat manually</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                disabled={!deviceState.isOnline || !deviceState.deviceId}
                checked={latest?.relay_on || false}
                onChange={handleToggleHeater}
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          {!deviceState.isOnline && (
            <div className="text-xs text-red-500 mt-2">Device is offline. Controls disabled.</div>
          )}
        </div>
      </div>

      <PredictionCard prediction={prediction} />
      
      <WaterLogChart logs={waterLogs} />

      <div className="section-title" style={{ marginTop: "40px" }}>
        <h3>Water logs</h3>
        <button className="btn btn-secondary" onClick={() => setShowWaterForm(true)}>
          + Log reading
        </button>
      </div>
      {waterLogs.length === 0 ? (
        <div className="empty-state">No water logs yet.</div>
      ) : (
        <div className="log-list">
          {waterLogs.map((log) => (
            <div className="log-row" key={log.id}>
              <div>
                <div className="log-row__readings" style={{ alignItems: "center" }}>
                  <span>{log.temperature}&deg;C</span>
                  <span style={{ display: "flex", alignItems: "center" }}>
                    pH {log.pH}
                    <PhSourceBadge isEstimated={log.ph_is_estimated} />
                  </span>
                  <span>{log.turbidity} NTU</span>
                </div>
                <div className="log-row__meta">{new Date(log.recorded_at).toLocaleString()}</div>
                {log.warnings?.length > 0 && (
                  <div className="log-row__warnings">{log.warnings[0]}</div>
                )}
              </div>
              <StatusBadge status={log.status} />
            </div>
          ))}
        </div>
      )}

      {showWaterForm && (
        <Modal title="Log a water reading" onClose={() => setShowWaterForm(false)}>
          <WaterLogForm onSubmit={handleAddWaterLog} submitting={submitting} error={formError} />
        </Modal>
      )}

    </>
  );
}
