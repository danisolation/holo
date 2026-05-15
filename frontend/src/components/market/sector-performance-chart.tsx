"use client";

import { useMemo } from "react";
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
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { SectorDetailTickerItem } from "@/lib/api";

interface SectorPerformanceChartProps {
  tickers: SectorDetailTickerItem[];
}

export function SectorPerformanceChart({
  tickers,
}: SectorPerformanceChartProps) {
  const chartData = useMemo(() => {
    // Sort by change_7d desc, take top 20 for readability
    const sorted = [...tickers]
      .filter((t) => t.change_7d != null || t.change_30d != null)
      .sort((a, b) => (b.change_7d ?? -999) - (a.change_7d ?? -999))
      .slice(0, 20);

    return sorted.map((t) => ({
      symbol: t.symbol,
      name: t.name,
      change_7d: t.change_7d ?? 0,
      change_30d: t.change_30d ?? 0,
    }));
  }, [tickers]);

  if (chartData.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hiệu suất ngành</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              dataKey="symbol"
              tick={{ fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            />
            <Tooltip
              formatter={(value: unknown, name: unknown) => [
                `${Number(value).toFixed(2)}%`,
                String(name),
              ]}
              labelFormatter={(label) => {
                const item = chartData.find((d) => d.symbol === String(label));
                return item ? `${item.symbol} - ${item.name}` : String(label);
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="change_7d"
              name="% 7 ngày"
              stroke="#26a69a"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="change_30d"
              name="% 30 ngày"
              stroke="#42a5f5"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
