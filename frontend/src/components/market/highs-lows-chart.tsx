"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HighsLowsItem } from "@/lib/api";
import {
  BarChart,
  Bar,
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

interface HLTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string }>;
  label?: string;
}

function HLTooltip({ active, payload, label }: HLTooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const parts = label.split("-");
  const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
  const highs = payload.find((p) => p.dataKey === "new_highs");
  const lows = payload.find((p) => p.dataKey === "new_lows");
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="text-muted-foreground mb-1">{formattedDate}</p>
      <p style={{ color: "var(--trading-bull)" }}>High 52W: {highs?.value ?? 0}</p>
      <p style={{ color: "var(--trading-bear)" }}>Low 52W: {lows?.value ?? 0}</p>
    </div>
  );
}

interface HighsLowsChartProps {
  data: HighsLowsItem[];
}

export function HighsLowsChart({ data }: HighsLowsChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">52-Week Highs vs Lows</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ minHeight: 300 }}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 12 }} width={40} />
              <Tooltip content={<HLTooltip />} />
              <Legend />
              <Bar dataKey="new_highs" name="High 52W" fill="#26a69a" radius={[2, 2, 0, 0]} />
              <Bar dataKey="new_lows" name="Low 52W" fill="#ef5350" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
