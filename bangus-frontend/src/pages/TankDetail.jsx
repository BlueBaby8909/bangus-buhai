import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import RangeGauge from "../components/RangeGauge";
import Modal from "../components/Modal";
import WaterLogForm from "../components/WaterLogForm";
import FeedingLogForm from "../components/FeedingLogForm";
import { THRESHOLDS, toneForMetric } from "../lib/waterQuality";

export default function TankDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [waterLogs, setWaterLogs] = useState([]);
  const [feedingLogs, setFeedingLogs] = useState([]);
  const [tab, setTab] = useState("water");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showWaterForm, setShowWaterForm] = useState(false);
  const [showFeedingForm, setShowFeedingForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.getTankSummary(id),
      api.listWaterLogs(id, { limit: 50 }),
      api.listFeedingLogs(id, { limit: 50 }),
    ])
      .then(([s, logs, feedings]) => {
        setSummary(s);
        setWaterLogs(logs.slice().reverse());
        setFeedingLogs(feedings.slice().reverse());
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

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

  const handleAddFeeding = async (data) => {
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createFeedingLog(id, data);
      setShowFeedingForm(false);
      loadAll();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Could not save feeding.");
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
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
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
        <div className="summary-tile">
          <div className="summary-tile__label">Feedings</div>
          <div className="summary-tile__value mono">{summary.total_feedings}</div>
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
          <h3 style={{ marginBottom: "8px" }}>Latest feeding</h3>
          {summary.latest_feeding ? (
            <>
              <p className="mono" style={{ fontSize: 18, marginBottom: 4 }}>
                {summary.latest_feeding.amount_grams}g &mdash; {summary.latest_feeding.feed_type}
              </p>
              <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>
                {new Date(summary.latest_feeding.fed_at).toLocaleString()}
              </p>
              {summary.latest_feeding.notes && (
                <p style={{ marginTop: 8, fontSize: 13 }}>{summary.latest_feeding.notes}</p>
              )}
            </>
          ) : (
            <p style={{ color: "var(--ink-soft)" }}>No feedings logged yet.</p>
          )}
        </div>
      </div>

      <div className="tabs" style={{ marginTop: "40px" }}>
        <button className={`tab ${tab === "water" ? "active" : ""}`} onClick={() => setTab("water")}>
          Water logs
        </button>
        <button className={`tab ${tab === "feeding" ? "active" : ""}`} onClick={() => setTab("feeding")}>
          Feeding logs
        </button>
      </div>

      {tab === "water" && (
        <>
          <div className="section-title">
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
                    <div className="log-row__readings">
                      <span>{log.temperature}&deg;C</span>
                      <span>pH {log.pH}</span>
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
        </>
      )}

      {tab === "feeding" && (
        <>
          <div className="section-title">
            <h3>Feeding logs</h3>
            <button className="btn btn-secondary" onClick={() => setShowFeedingForm(true)}>
              + Log feeding
            </button>
          </div>
          {feedingLogs.length === 0 ? (
            <div className="empty-state">No feedings logged yet.</div>
          ) : (
            <div className="log-list">
              {feedingLogs.map((f) => (
                <div className="log-row" key={f.id}>
                  <div>
                    <div className="log-row__readings">
                      <span className="mono">{f.amount_grams}g</span>
                      <span>{f.feed_type}</span>
                    </div>
                    <div className="log-row__meta">{new Date(f.fed_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {showWaterForm && (
        <Modal title="Log a water reading" onClose={() => setShowWaterForm(false)}>
          <WaterLogForm onSubmit={handleAddWaterLog} submitting={submitting} error={formError} />
        </Modal>
      )}
      {showFeedingForm && (
        <Modal title="Log a feeding" onClose={() => setShowFeedingForm(false)}>
          <FeedingLogForm onSubmit={handleAddFeeding} submitting={submitting} error={formError} />
        </Modal>
      )}
    </>
  );
}
