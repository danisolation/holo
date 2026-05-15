"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MABreadthItem } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

function formatDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

interface MATooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string }>;
  label?: string;
}

function MATooltip({ active, payload, label }: MATooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const parts = label.split("-");
  const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
  const ma50 = payload.find((p) => p.dataKey === "pct_above_ma50");
  const ma200 = payload.find((p) => p.dataKey === "pct_above_ma200");
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="text-muted-foreground mb-1">{formattedDate}</p>
      <p style={{ color: "#2196f3" }}>% &gt; MA50: {ma50?.value?.toFixed(1) ?? "—"}%</p>
      <p style={{ color: "#ff9800" }}>% &gt; MA200: {ma200?.value?.toFixed(1) ?? "—"}%</p>
    </div>
  );
}

interface MABreadthChartProps {
  data: MABreadthItem[];
}

export function MABreadthChart({ data }: MABreadthChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">MA Breadth — % Trên MA50/MA200</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ minHeight: 300 }}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12 }}
                width={40}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip content={<MATooltip />} />
              <Legend />
              <ReferenceLine
                y={50}
                stroke="#9e9e9e"
                strokeDasharray="5 5"
              />
              <Line
                type="monotone"
                dataKey="pct_above_ma50"
                name="% > MA50"
                stroke="#2196f3"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="pct_above_ma200"
                name="% > MA200"
                stroke="#ff9800"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
