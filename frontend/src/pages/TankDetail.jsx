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
import { MLPredictions } from "../components/MLPredictions";
import { RelayControl } from "../components/RelayControl";
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
  const [optimisticRelay, setOptimisticRelay] = useState(null);

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
        if (s?.latest_water_log) {
          setOptimisticRelay(s.latest_water_log.relay_on);
        }
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
            setOptimisticRelay(data.water_log.relay_on);
          } else if (data.type === "device_status") {
            setDeviceState(prev => ({ ...prev, isOnline: data.is_online, deviceId: data.device_id || prev.deviceId }));
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

        <RelayControl 
          deviceId={deviceState.deviceId} 
          initialRelayState={optimisticRelay ?? (latest?.relay_on || false)} 
          disabled={!deviceState.isOnline} 
        />
      </div>

      <MLPredictions prediction={prediction} />
      
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
