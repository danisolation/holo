"use client";

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { usePerformanceData } from "@/lib/hooks";
import { formatVND, formatCompactVND } from "@/lib/format";

const PERIODS = [
  { value: "1M", label: "1T" },
  { value: "3M", label: "3T" },
  { value: "6M", label: "6T" },
  { value: "1Y", label: "1N" },
  { value: "ALL", label: "Tất cả" },
] as const;

const LONG_PERIODS = new Set(["1Y", "ALL"]);

function formatDateTick(dateStr: string, period: string): string {
  const [year, month, day] = dateStr.split("-");
  if (LONG_PERIODS.has(period)) {
    return `${month}/${year.slice(2)}`;
  }
  return `${day}/${month}`;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length || !label) return null;

  const [year, month, day] = label.split("-");
  const formattedDate = `${day}/${month}/${year}`;

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
        {formatVND(payload[0].value)} ₫
      </p>
    </div>
  );
}

export function PerformanceChart() {
  const [period, setPeriod] = useState("3M");
  const { data, isLoading } = usePerformanceData(period);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <CardTitle className="text-lg font-semibold">
            Giá trị danh mục
          </CardTitle>
          <Tabs
            value={period}
            onValueChange={(v) => setPeriod(v as string)}
            className="sm:ml-auto"
          >
            <TabsList className="h-7">
              {PERIODS.map((p) => (
                <TabsTrigger key={p.value} value={p.value} className="text-xs px-2">
                  {p.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-80 w-full rounded-lg" />
        ) : !data?.data?.length ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu hiệu suất. Thêm giao dịch để bắt đầu theo dõi.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={data.data}>
              <defs>
                <linearGradient id="perfGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke="var(--border)"
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                tickFormatter={(d) => formatDateTick(d, period)}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                width={60}
                tickFormatter={formatCompactVND}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#perfGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
