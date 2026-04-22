"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktestLatest, useBacktestAnalytics } from "@/lib/hooks";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

function formatCompactVND(value: number): string {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function SectorTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  return (
    <div className="rounded-lg border bg-popover p-3 text-sm shadow-md">
      <p className="font-semibold mb-1">{label}</p>
      <p>Lệnh: {item.total_trades}</p>
      <p>Win Rate: {item.win_rate.toFixed(1)}%</p>
      <p className={item.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
        Tổng P&L: {item.total_pnl >= 0 ? "+" : ""}
        {formatVND(item.total_pnl)}
      </p>
      <p className={item.avg_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
        TB P&L: {item.avg_pnl >= 0 ? "+" : ""}
        {formatVND(item.avg_pnl)}
      </p>
    </div>
  );
}

function ConfidenceTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  return (
    <div className="rounded-lg border bg-popover p-3 text-sm shadow-md">
      <p className="font-semibold mb-1">{label}</p>
      <p>Lệnh: {item.total_trades}</p>
      <p>Thắng: {item.wins}</p>
      <p>Win Rate: {item.win_rate.toFixed(1)}%</p>
      <p className={item.avg_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
        TB P&L: {item.avg_pnl >= 0 ? "+" : ""}
        {formatVND(item.avg_pnl)}
      </p>
      <p>TB P&L %: {item.avg_pnl_pct.toFixed(2)}%</p>
    </div>
  );
}

function TimeframeTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  return (
    <div className="rounded-lg border bg-popover p-3 text-sm shadow-md">
      <p className="font-semibold mb-1">{label}</p>
      <p>Lệnh: {item.total_trades}</p>
      <p>Thắng: {item.wins}</p>
      <p>Win Rate: {item.win_rate.toFixed(1)}%</p>
      <p>TB ngày giữ: {item.avg_holding_days.toFixed(1)}</p>
      <p className={item.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
        Tổng P&L: {item.total_pnl >= 0 ? "+" : ""}
        {formatVND(item.total_pnl)}
      </p>
      <p className={item.avg_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
        TB P&L: {item.avg_pnl >= 0 ? "+" : ""}
        {formatVND(item.avg_pnl)}
      </p>
    </div>
  );
}
/* eslint-enable @typescript-eslint/no-explicit-any */

export function BTAnalyticsTab() {
  const { data: latestRun } = useBacktestLatest(false);
  const runId =
    latestRun?.status === "completed" ? latestRun.id : undefined;
  const { data, isLoading } = useBacktestAnalytics(runId);

  if (!latestRun || latestRun.status !== "completed") {
    return (
      <div
        data-testid="bt-analytics-content"
        className="py-8 text-center text-muted-foreground text-sm"
      >
        Chưa có kết quả backtest. Vui lòng chạy backtest từ tab Cấu hình.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div data-testid="bt-analytics-content" className="space-y-6 mt-4">
        <Skeleton className="h-80 w-full rounded-lg" />
        <Skeleton className="h-80 w-full rounded-lg" />
        <Skeleton className="h-80 w-full rounded-lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <div
        data-testid="bt-analytics-content"
        className="py-8 text-center text-muted-foreground text-sm"
      >
        Chưa có dữ liệu phân tích.
      </div>
    );
  }

  const { sectors, confidence, timeframes } = data;

  return (
    <div data-testid="bt-analytics-content" className="space-y-6 mt-4">
      {/* Section 1: Sector Breakdown — horizontal bars */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Phân tích theo ngành
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sectors.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Chưa có dữ liệu ngành.
            </p>
          ) : (
            <ResponsiveContainer
              width="100%"
              height={Math.max(300, sectors.length * 40)}
            >
              <BarChart data={sectors} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <YAxis
                  dataKey="sector"
                  type="category"
                  width={120}
                  tick={{ fontSize: 12 }}
                />
                <XAxis type="number" tickFormatter={formatCompactVND} />
                <Tooltip content={<SectorTooltip />} />
                <Legend />
                <Bar dataKey="total_pnl" name="Tổng P&L" fill="#3b82f6" />
                <Bar dataKey="avg_pnl" name="TB P&L/lệnh" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Confidence Breakdown — vertical bars with conditional coloring */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Phân tích theo độ tin cậy
          </CardTitle>
        </CardHeader>
        <CardContent>
          {confidence.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Chưa có dữ liệu độ tin cậy.
            </p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={confidence} margin={{ top: 10, right: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="bracket" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={formatCompactVND} />
                  <Tooltip content={<ConfidenceTooltip />} />
                  <Bar dataKey="avg_pnl" name="TB P&L/lệnh" radius={[4, 4, 0, 0]}>
                    {confidence.map((entry, idx) => (
                      <Cell
                        key={idx}
                        fill={entry.avg_pnl >= 0 ? "#26a69a" : "#ef5350"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {/* Best bracket summary */}
              {(() => {
                const best = [...confidence].sort(
                  (a, b) => b.avg_pnl - a.avg_pnl
                )[0];
                return best ? (
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    Nhóm tốt nhất:{" "}
                    <Badge variant="secondary" className="text-xs">
                      {best.bracket}
                    </Badge>{" "}
                    — Win Rate {best.win_rate.toFixed(1)}%, TB P&L{" "}
                    <span
                      className={
                        best.avg_pnl >= 0
                          ? "text-[#26a69a]"
                          : "text-[#ef5350]"
                      }
                    >
                      {best.avg_pnl >= 0 ? "+" : ""}
                      {formatVND(best.avg_pnl)}
                    </span>
                  </p>
                ) : null;
              })()}
            </>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Timeframe/Holding Period Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Phân tích theo thời gian giữ lệnh
          </CardTitle>
        </CardHeader>
        <CardContent>
          {timeframes.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Chưa có dữ liệu thời gian giữ.
            </p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={timeframes} margin={{ top: 10, right: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={formatCompactVND} />
                  <Tooltip content={<TimeframeTooltip />} />
                  <Bar
                    dataKey="total_pnl"
                    name="Tổng P&L"
                    radius={[4, 4, 0, 0]}
                  >
                    {timeframes.map((entry, idx) => (
                      <Cell
                        key={idx}
                        fill={entry.total_pnl >= 0 ? "#26a69a" : "#ef5350"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              {/* Summary table */}
              <div className="overflow-x-auto mt-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="text-left py-2 font-medium">Nhóm</th>
                      <th className="text-right py-2 font-medium">Lệnh</th>
                      <th className="text-right py-2 font-medium">Win Rate</th>
                      <th className="text-right py-2 font-medium">
                        TB Ngày giữ
                      </th>
                      <th className="text-right py-2 font-medium">Tổng P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {timeframes.map((item) => (
                      <tr
                        key={item.bucket}
                        className="border-b last:border-0"
                      >
                        <td className="py-2 font-medium">{item.bucket}</td>
                        <td className="py-2 text-right">{item.total_trades}</td>
                        <td className="py-2 text-right">
                          <Badge
                            variant={
                              item.win_rate >= 50 ? "default" : "destructive"
                            }
                            className="text-xs"
                          >
                            {item.win_rate.toFixed(1)}%
                          </Badge>
                        </td>
                        <td className="py-2 text-right font-mono">
                          {item.avg_holding_days.toFixed(1)}d
                        </td>
                        <td
                          className={`py-2 text-right font-mono ${
                            item.total_pnl >= 0
                              ? "text-[#26a69a]"
                              : "text-[#ef5350]"
                          }`}
                        >
                          {item.total_pnl >= 0 ? "+" : ""}
                          {formatVND(item.total_pnl)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
