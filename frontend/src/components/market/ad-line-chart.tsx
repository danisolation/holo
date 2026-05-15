"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ADLineItem } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

function formatDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

interface ADLineTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; color: string }>;
  label?: string;
}

function ADLineTooltip({ active, payload, label }: ADLineTooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const parts = label.split("-");
  const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
  const adv = payload.find((p) => p.dataKey === "advancing");
  const dec = payload.find((p) => p.dataKey === "declining");
  const net = (adv?.value ?? 0) - (dec?.value ?? 0);
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="text-muted-foreground mb-1">{formattedDate}</p>
      <p style={{ color: "#26a69a" }}>Tăng: {adv?.value ?? 0}</p>
      <p style={{ color: "#ef5350" }}>Giảm: {dec?.value ?? 0}</p>
      <p className="font-semibold mt-1">Net: {net > 0 ? "+" : ""}{net}</p>
    </div>
  );
}

interface ADLineChartProps {
  data: ADLineItem[];
}

export function ADLineChart({ data }: ADLineChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">A/D Line — Tăng/Giảm</CardTitle>
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
              <YAxis tick={{ fontSize: 12 }} width={50} />
              <Tooltip content={<ADLineTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="advancing"
                name="Tăng"
                stroke="#26a69a"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                fillOpacity={0.1}
              />
              <Line
                type="monotone"
                dataKey="declining"
                name="Giảm"
                stroke="#ef5350"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
                fillOpacity={0.1}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
