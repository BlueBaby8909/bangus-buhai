export function DeviceStatus({ isOnline, lastSeen, style = {} }) {
  if (isOnline === undefined) return null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", fontWeight: "500", ...style }}>
      <div style={{ position: "relative", display: "flex", height: "12px", width: "12px" }}>
        {isOnline && (
          <span 
            className="pulse-ring" 
            style={{ position: "absolute", height: "100%", width: "100%", borderRadius: "50%", backgroundColor: "#4ade80", opacity: 0.75 }}
          ></span>
        )}
        <span
          style={{ position: "relative", display: "inline-flex", borderRadius: "50%", height: "12px", width: "12px", backgroundColor: isOnline ? "#22c55e" : "#9ca3af" }}
        ></span>
      </div>
      <span style={{ color: isOnline ? "var(--ink)" : "var(--ink-soft)" }}>
        {isOnline ? "Device Online" : "Device Offline"}
      </span>
      {!isOnline && lastSeen && (
        <span style={{ fontSize: "12px", color: "var(--ink-soft)", fontWeight: "normal" }}>
          Last seen: {new Date(lastSeen).toLocaleString()}
        </span>
      )}
    </div>
  );
}
