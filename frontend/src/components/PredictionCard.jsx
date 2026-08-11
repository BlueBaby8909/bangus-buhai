import React from 'react';
import { format } from 'date-fns';

export function PredictionCard({ prediction }) {
  if (!prediction) return null;

  // Bangus ideal thresholds (example)
  const isTempIdeal = prediction.temperature >= 26 && prediction.temperature <= 32;
  const isPhIdeal = prediction.pH >= 7.5 && prediction.pH <= 8.5;
  const isTurbidityIdeal = prediction.turbidity <= 50; // Adjust as needed

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-blue-50 p-6 rounded-xl border border-indigo-100 shadow-sm mt-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-indigo-900">AI Forecast</h3>
        <span className="bg-indigo-100 text-indigo-800 text-xs px-2 py-1 rounded-full font-medium">
          3-Hour Horizon
        </span>
      </div>
      
      <p className="text-sm text-indigo-600 mb-6">
        Predicted state for {format(new Date(prediction.predicted_for), "h:mm a, MMM d")}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Temperature */}
        <div className={`p-4 rounded-lg bg-white border ${isTempIdeal ? 'border-gray-100' : 'border-red-200 shadow-sm'}`}>
          <div className="text-sm text-gray-500 mb-1">Temperature</div>
          <div className={`text-2xl font-bold ${isTempIdeal ? 'text-gray-800' : 'text-red-600'}`}>
            {prediction.temperature.toFixed(1)}°C
          </div>
          {!isTempIdeal && (
            <div className="text-xs text-red-500 mt-1 flex items-center">
              <span className="material-icons text-[14px] mr-1">warning</span>
              Out of range
            </div>
          )}
        </div>

        {/* pH */}
        <div className={`p-4 rounded-lg bg-white border ${isPhIdeal ? 'border-gray-100' : 'border-red-200 shadow-sm'}`}>
          <div className="text-sm text-gray-500 mb-1">pH Level</div>
          <div className={`text-2xl font-bold ${isPhIdeal ? 'text-gray-800' : 'text-red-600'}`}>
            {prediction.pH.toFixed(2)}
          </div>
          {!isPhIdeal && (
            <div className="text-xs text-red-500 mt-1 flex items-center">
              <span className="material-icons text-[14px] mr-1">warning</span>
              Out of range
            </div>
          )}
        </div>

        {/* Turbidity */}
        <div className={`p-4 rounded-lg bg-white border ${isTurbidityIdeal ? 'border-gray-100' : 'border-red-200 shadow-sm'}`}>
          <div className="text-sm text-gray-500 mb-1">Turbidity</div>
          <div className={`text-2xl font-bold ${isTurbidityIdeal ? 'text-gray-800' : 'text-red-600'}`}>
            {prediction.turbidity.toFixed(1)} NTU
          </div>
          {!isTurbidityIdeal && (
            <div className="text-xs text-red-500 mt-1 flex items-center">
              <span className="material-icons text-[14px] mr-1">warning</span>
              Out of range
            </div>
          )}
        </div>
      </div>
      
      {prediction.confidence_score < 1.0 && (
        <div className="mt-4 text-xs text-indigo-500 flex items-center">
          <span className="material-icons text-[14px] mr-1">info</span>
          Forecast confidence reduced due to missing sensor data (default values used).
        </div>
      )}
    </div>
  );
}
