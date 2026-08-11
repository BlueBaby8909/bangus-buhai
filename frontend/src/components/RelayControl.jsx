import React, { useState } from 'react';
import { api } from '../api/client';

export function RelayControl({ deviceId, initialRelayState = false, disabled = false }) {
  const [isOn, setIsOn] = useState(initialRelayState);
  const [isPending, setIsPending] = useState(false);

  const handleToggle = async () => {
    if (disabled || isPending || !deviceId) return;
    
    // Optimistic UI update
    const previousState = isOn;
    const newState = !isOn;
    
    setIsOn(newState);
    setIsPending(true);

    try {
      await api.sendCommand(deviceId, {
        relay: "relay_1",
        state: newState
      });
      // The websocket should broadcast the true state eventually, 
      // but we assume it worked if no error was thrown.
    } catch (err) {
      console.error("Failed to toggle relay:", err);
      // Revert on error
      setIsOn(previousState);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="glass-panel p-6 mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 border border-white/10">
      <div className="flex items-center gap-4">
        <div className={`flex items-center justify-center w-12 h-12 rounded-full shadow-inner ${isOn ? 'bg-sky-500/20 text-sky-400' : 'bg-white/5 text-slate-400'}`}>
          <span className="material-icons">{isOn ? 'power' : 'power_off'}</span>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">Heater Relay</h3>
          <p className="text-sm text-slate-400">
            {deviceId ? `Device ID: ${deviceId}` : "No device claimed"}
          </p>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <span className={`text-sm font-medium ${isOn ? 'text-sky-400' : 'text-slate-500'}`}>
          {isOn ? 'ACTIVE' : 'INACTIVE'}
        </span>
        <button 
          onClick={handleToggle}
          disabled={disabled || isPending || !deviceId}
          className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
            isOn ? 'bg-sky-500' : 'bg-slate-600'
          } ${(disabled || isPending) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform duration-300 shadow-sm ${
              isOn ? 'translate-x-8' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );
}
