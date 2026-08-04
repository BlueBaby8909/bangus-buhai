import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import GaugeRing from "./GaugeRing";

export default function TankCard({ tank }) {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let alive = true;
    api
      .getTankSummary(tank.id)
      .then((data) => alive && setSummary(data))
      .catch(() => alive && setSummary(null));
    return () => {
      alive = false;
    };
  }, [tank.id]);

  const status = summary?.latest_water_log?.status || "unknown";

  return (
    <div className="card tank-card" onClick={() => navigate(`/tanks/${tank.id}`)}>
      <div className="tank-card__top">
        <div>
          <div className="tank-card__name">{tank.name}</div>
          <div className="tank-card__stage">{tank.growth_stage}</div>
        </div>
        <GaugeRing status={status} size={64} />
      </div>

      <div className="tank-card__stats">
        <div>
          <div className="tank-card__stat-label">Volume</div>
          <div className="tank-card__stat-value mono">{tank.volume_ml.toLocaleString()} mL</div>
        </div>
        <div>
          <div className="tank-card__stat-label">Capacity</div>
          <div className="tank-card__stat-value mono">{tank.capacity.toLocaleString()}</div>
        </div>
        <div>
          <div className="tank-card__stat-label">Since</div>
          <div className="tank-card__stat-value">{tank.date_added}</div>
        </div>
      </div>
    </div>
  );
}
