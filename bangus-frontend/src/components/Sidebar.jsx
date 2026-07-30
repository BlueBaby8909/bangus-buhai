import { NavLink } from "react-router-dom";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="var(--water-tint)" />
          <path
            d="M6 16c4-6 12-8 18-4-2 2-2 6 0 8-6 4-14 2-18-4z"
            fill="var(--ink)"
          />
          <circle cx="10.5" cy="14.5" r="1.2" fill="var(--water-tint)" />
        </svg>
        <div>
          <div className="sidebar__brand-name">Bangus Buhai</div>
          <div className="sidebar__brand-tag">Pond &amp; tank log</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        <NavLink to="/" end className="sidebar__link">
          Tanks
        </NavLink>
        <NavLink to="/users" className="sidebar__link">
          Growers
        </NavLink>
      </nav>

      <div className="sidebar__footer">
        <p>Readings follow general milkfish culture ranges — check locally for site-specific thresholds.</p>
      </div>
    </aside>
  );
}
