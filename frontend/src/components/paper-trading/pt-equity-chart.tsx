"use client";

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
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperEquityCurve, usePaperDrawdown } from "@/lib/hooks";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

function formatCompactVND(value: number): string {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { date: string; daily_pnl: number; cumulative_pnl: number } }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
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
        P&L ngày:{" "}
        <span className={point.daily_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
          {point.daily_pnl >= 0 ? "+" : ""}
          {formatVND(point.daily_pnl)} ₫
        </span>
      </p>
      <p className="text-sm font-semibold font-mono">
        Tích lũy:{" "}
        <span className={point.cumulative_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
          {point.cumulative_pnl >= 0 ? "+" : ""}
          {formatVND(point.cumulative_pnl)} ₫
        </span>
      </p>
    </div>
  );
}

export function PTEquityChart() {
  const { data: equityCurve, isLoading: loadingEquity } = usePaperEquityCurve();
  const { data: drawdown, isLoading: loadingDrawdown } = usePaperDrawdown();

  const isLoading = loadingEquity || loadingDrawdown;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Đường cong vốn</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-80 w-full rounded-lg" />
        ) : !equityCurve?.data?.length ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu đường cong vốn.
            </p>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={equityCurve.data}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
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
                  tickFormatter={formatCompactVND}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cumulative_pnl"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#equityGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>

            {/* Drawdown summary */}
            {drawdown && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">DD tối đa</p>
                    <p className="text-xl font-bold font-mono text-[#ef5350]">
                      {formatVND(drawdown.max_drawdown_vnd)} ₫
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {drawdown.max_drawdown_pct.toFixed(2)}%
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">DD hiện tại</p>
                    <p
                      className={`text-xl font-bold font-mono ${
                        drawdown.current_drawdown_vnd < 0
                          ? "text-[#ef5350]"
                          : "text-[#26a69a]"
                      }`}
                    >
                      {formatVND(drawdown.current_drawdown_vnd)} ₫
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {drawdown.current_drawdown_pct.toFixed(2)}%
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
