"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export interface EquityCurveChartProps {
  data: { date: string; value: number }[];
  benchmarkData?: { date: string; value: number }[];
  label?: string;
  benchmarkLabel?: string;
  height?: number;
  formatValue?: (value: number) => string;
  formatYAxis?: (value: number) => string;
}

interface MergedPoint {
  date: string;
  value: number;
  benchmark?: number | null;
}

function ChartTooltip({
  active,
  payload,
  label,
  seriesLabel,
  benchmarkSeriesLabel,
  formatFn,
}: {
  active?: boolean;
  payload?: Array<{ payload: MergedPoint }>;
  label?: string;
  seriesLabel: string;
  benchmarkSeriesLabel?: string;
  formatFn: (v: number) => string;
}) {
  if (!active || !payload?.length || !label) return null;

  const [year, month, day] = label.split("-");
  const formattedDate = `${day}/${month}/${year}`;
  const point = payload[0].payload;

  return (
    <div
      className="rounded-md border shadow-md"
      style={{
        background: "var(--popover)",
        borderColor: "var(--border)",
        padding: "8px 12px",
      }}
    >
      <p className="text-xs text-muted-foreground">{formattedDate}</p>
      <p className="text-sm font-semibold font-mono">
        {seriesLabel}:{" "}
        <span
          className={
            point.value >= 0 ? "text-[#3b82f6]" : "text-[#ef5350]"
          }
        >
          {point.value >= 0 ? "+" : ""}
          {formatFn(point.value)}
        </span>
      </p>
      {benchmarkSeriesLabel != null && point.benchmark != null && (
        <p className="text-sm font-semibold font-mono">
          {benchmarkSeriesLabel}:{" "}
          <span className="text-[#f59e0b]">
            {point.benchmark >= 0 ? "+" : ""}
            {formatFn(point.benchmark)}
          </span>
        </p>
      )}
    </div>
  );
}

export function EquityCurveChart({
  data,
  benchmarkData,
  label = "Value",
  benchmarkLabel,
  height = 320,
  formatValue = (v) => v.toFixed(2),
  formatYAxis,
}: EquityCurveChartProps) {
  const yAxisFormatter = formatYAxis ?? formatValue;

  const mergedData: MergedPoint[] = useMemo(() => {
    if (!benchmarkData?.length) {
      return data.map((d) => ({ date: d.date, value: d.value }));
    }
    const benchMap = new Map(benchmarkData.map((b) => [b.date, b.value]));
    return data.map((d) => ({
      date: d.date,
      value: d.value,
      benchmark: benchMap.get(d.date) ?? null,
    }));
  }, [data, benchmarkData]);

  const gradientId = `equity-gradient-${label.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={mergedData}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
          tickFormatter={(d: string) => {
            const [, m, dd] = d.split("-");
            return `${dd}/${m}`;
          }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
          width={60}
          tickFormatter={yAxisFormatter}
        />
        <Tooltip
          content={
            <ChartTooltip
              seriesLabel={label}
              benchmarkSeriesLabel={benchmarkLabel}
              formatFn={formatValue}
            />
          }
        />
        {benchmarkData && benchmarkData.length > 0 && <Legend />}
        <Area
          type="monotone"
          dataKey="value"
          name={label}
          stroke="#3b82f6"
          strokeWidth={2}
          fill={`url(#${gradientId})`}
        />
        {benchmarkData && benchmarkData.length > 0 && (
          <Line
            type="monotone"
            dataKey="benchmark"
            name={benchmarkLabel}
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
