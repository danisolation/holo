"use client";

import { useMemo } from "react";
import { useEquityHistory } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

/** Format VND value with millions abbreviation: 100,000,000 → "100.0tr" */
function formatVND(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}tỷ`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}tr`;
  }
  return value.toLocaleString("vi-VN");
}

/** Format full VND value: 100,000,000 → "100,000,000 ₫" */
function formatVNDFull(value: number): string {
  return `${value.toLocaleString("vi-VN")} ₫`;
}

/** Format date string "2025-01-15" → "15/01" */
function formatDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length || !label) return null;
  const parts = label.split("-");
  const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="text-muted-foreground">{formattedDate}</p>
      <p className="font-semibold">{formatVNDFull(payload[0].value)}</p>
    </div>
  );
}

export function EquityChart() {
  const { data, isLoading } = useEquityHistory();

  const lineColor = useMemo(() => {
    if (!data?.history || data.history.length === 0) return "#26a69a";
    const last = data.history[data.history.length - 1].equity;
    return last >= data.starting_capital ? "#26a69a" : "#ef5350";
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Biểu đồ vốn</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-12 text-center">
            Đang tải biểu đồ...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data?.history || data.history.length <= 1) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Biểu đồ vốn</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-12 text-center">
            Chưa có dữ liệu giao dịch
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Biểu đồ vốn</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ minHeight: 300 }}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.history}>
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={formatVND}
                tick={{ fontSize: 12 }}
                width={70}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={data.starting_capital}
                stroke="#9e9e9e"
                strokeDasharray="5 5"
                label={{ value: "Vốn ban đầu", position: "right", fontSize: 11, fill: "#9e9e9e" }}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke={lineColor}
                strokeWidth={2}
                dot={data.history.length <= 20}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
