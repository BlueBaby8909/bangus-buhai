import React from 'react';
import { format, addHours } from 'date-fns';

export function MLPredictions({ prediction }) {
  if (!prediction) return null;

  // Render a single horizon column
  const renderHorizon = (horizonName, hoursAhead, temp, ph, turbidity) => {
    const isTempIdeal = temp >= 26 && temp <= 32;
    const isPhIdeal = ph >= 7.5 && ph <= 8.5;
    const isTurbidityIdeal = turbidity <= 50;
    const time = addHours(new Date(prediction.predicted_from), hoursAhead);

    return (
      <div key={horizonName} className="flex flex-col gap-3 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
        <div className="text-sm font-semibold text-sky-400 mb-2">
          {horizonName}
          <div className="text-xs text-slate-400 font-normal">{format(time, "h:mm a")}</div>
        </div>
        
        {/* Temp */}
        <div className={`flex justify-between items-center ${isTempIdeal ? 'text-slate-200' : 'text-red-400 font-medium'}`}>
          <span className="text-xs text-slate-400">Temp</span>
          <span>{temp.toFixed(1)}°C</span>
        </div>
        
        {/* pH */}
        <div className={`flex justify-between items-center ${isPhIdeal ? 'text-slate-200' : 'text-red-400 font-medium'}`}>
          <span className="text-xs text-slate-400">pH</span>
          <span>{ph.toFixed(2)}</span>
        </div>
        
        {/* Turbidity */}
        <div className={`flex justify-between items-center ${isTurbidityIdeal ? 'text-slate-200' : 'text-red-400 font-medium'}`}>
          <span className="text-xs text-slate-400">Turb</span>
          <span>{turbidity.toFixed(1)} NTU</span>
        </div>
      </div>
    );
  };

  return (
    <div className="glass-panel p-6 mt-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="material-icons text-sky-400">auto_graph</span>
          AI Forecast
        </h3>
        <span className="bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs px-3 py-1 rounded-full font-medium">
          4-Hour Horizon
        </span>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {renderHorizon("+1 Hour", 1, prediction.temperature_1h, prediction.pH_1h, prediction.turbidity_1h)}
        {renderHorizon("+2 Hours", 2, prediction.temperature_2h, prediction.pH_2h, prediction.turbidity_2h)}
        {renderHorizon("+3 Hours", 3, prediction.temperature_3h, prediction.pH_3h, prediction.turbidity_3h)}
        {renderHorizon("+4 Hours", 4, prediction.temperature_4h, prediction.pH_4h, prediction.turbidity_4h)}
      </div>
      
      {prediction.confidence_score < 1.0 && (
        <div className="mt-6 text-xs text-amber-400/80 flex items-center bg-amber-500/10 p-2 rounded-lg">
          <span className="material-icons text-[14px] mr-2">info</span>
          Forecast confidence reduced due to missing sensor data (default values used).
        </div>
      )}
    </div>
  );
}
