import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { timestamp, display } from "./readings";
export default function TrendChart({ chart }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chart}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="time"
          type="number"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(n) =>
            new Date(n).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })
          }
        />
        <YAxis width={44} />
        <Tooltip
          labelFormatter={timestamp}
          formatter={(value, name, item) => [
            `${display(value)} (${item.payload.source})`,
            name,
          ]}
        />
        <Legend />
        <Line
          dataKey="device"
          name="Selected device"
          stroke="#003FB1"
          connectNulls={false}
          dot={{ r: 3 }}
          isAnimationActive={false}
        />
        <Line
          dataKey="manual"
          name="Manual measurement"
          stroke="#00664A"
          strokeWidth={0}
          dot={{ r: 5 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
