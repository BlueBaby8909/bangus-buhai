import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

export function WaterLogChart({ logs }) {
  if (!logs || logs.length === 0) {
    return (
      <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm mt-6 flex items-center justify-center h-48">
        <span className="text-gray-400">No historical data available</span>
      </div>
    );
  }

  // Format data for chart
  // logs are provided newest-first, so we reverse to plot left-to-right chronologically
  const data = [...logs].reverse().map((log) => ({
    time: new Date(log.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    temperature: log.temperature,
    pH: log.ph_source === 'sensor' ? log.pH : null, // only plot real pH
    turbidity: log.turbidity,
  }));

  return (
    <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm mt-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-6">Historical Trends</h3>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 5, left: -20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis 
              dataKey="time" 
              tick={{ fontSize: 12, fill: '#9ca3af' }} 
              tickMargin={10} 
              axisLine={false}
              tickLine={false}
              minTickGap={30}
            />
            
            {/* Left Axis for Temp and Turbidity (similar scales, 0-100) */}
            <YAxis 
              yAxisId="left" 
              tick={{ fontSize: 12, fill: '#9ca3af' }} 
              tickLine={false} 
              axisLine={false} 
            />
            
            {/* Right Axis for pH (0-14) */}
            <YAxis 
              yAxisId="right" 
              orientation="right" 
              domain={[0, 14]} 
              tick={{ fontSize: 12, fill: '#9ca3af' }} 
              tickLine={false} 
              axisLine={false} 
            />
            
            <Tooltip
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)' }}
            />
            <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
            
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="temperature"
              name="Temp (°C)"
              stroke="#ef4444"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="turbidity"
              name="Turbidity (NTU)"
              stroke="#eab308"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="pH"
              name="pH"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 0 }}
              connectNulls={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
