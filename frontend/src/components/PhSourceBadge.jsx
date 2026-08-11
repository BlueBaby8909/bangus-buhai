import { useState } from "react";

export function PhSourceBadge({ isEstimated }) {
  const [showTooltip, setShowTooltip] = useState(false);

  if (!isEstimated) return null;

  return (
    <div 
      style={{ position: "relative", display: "inline-flex", marginLeft: "8px" }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span 
        style={{
          display: "inline-flex", 
          alignItems: "center", 
          gap: "4px", 
          padding: "2px 8px", 
          borderRadius: "9999px", 
          fontSize: "12px", 
          fontWeight: "500",
          color: "#ea580c", 
          backgroundColor: "#fff7ed", 
          border: "1px solid #ffedd5",
          cursor: "help"
        }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        Estimated
      </span>
      
      {showTooltip && (
        <div style={{
          position: "absolute",
          bottom: "100%",
          left: "50%",
          transform: "translateX(-50%)",
          marginBottom: "8px",
          width: "250px",
          padding: "8px 12px",
          backgroundColor: "var(--ink)",
          color: "white",
          fontSize: "13px",
          borderRadius: "6px",
          zIndex: 10,
          boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
          lineHeight: "1.4"
        }}>
          The pH value is estimated because the device currently lacks a physical pH sensor. 
          This value is a system default and should not be relied upon for critical decisions.
        </div>
      )}
    </div>
  );
}
