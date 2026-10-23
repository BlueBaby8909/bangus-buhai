import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import FrameHeader from "./prototype/FrameHeader";
import { useAuth } from "./auth-context";

export default function AppHeader({ onError }) {
  const auth = useAuth(),
    { pathname } = useLocation(),
    account = useRef(null);
  const detail = pathname.startsWith("/tanks/");
  const title = detail
    ? "Tank details"
    : {
        "/": "Hatchery monitor",
        "/tanks": "Tanks",
        "/alerts": "Alerts",
        "/data": "Data export",
      }[pathname] || "Bangus BuhAI";
  const hatchery = auth.operator.hatcheries.find((h) => h.id === auth.hatchery);
  useEffect(() => {
    if (account.current?.matches(":popover-open"))
      account.current.hidePopover();
  }, [pathname]);
  return (
    <>
      <FrameHeader
        title={title}
        leftNode={
          <Link
            className={detail ? "header-back" : "header-brand"}
            to={detail ? "/tanks" : "/"}
            aria-label={detail ? "Back to tanks" : "Bangus BuhAI dashboard"}
          >
            {detail ? "←" : "B"}
          </Link>
        }
        rightNode={
          <button
            className="account-trigger"
            popoverTarget="workspace-account"
            aria-label="Account and hatchery"
          >
            <span className="account-hatchery">{hatchery?.name}</span>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <circle cx="12" cy="8" r="3.5" />
              <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
            </svg>
          </button>
        }
      />
      <div
        className="account-panel"
        id="workspace-account"
        popover="auto"
        ref={account}
      >
        <h2>Your workspace</h2>
        <label htmlFor="hatchery">Hatchery</label>
        <select
          id="hatchery"
          value={auth.hatchery}
          onChange={(e) => {
            auth.setHatchery(e.target.value);
            account.current.hidePopover();
          }}
        >
          {auth.operator.hatcheries.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
        <button onClick={() => auth.logout().catch(onError)}>Sign out</button>
      </div>
    </>
  );
}
