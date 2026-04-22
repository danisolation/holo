"use client";

import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperEquityCurve, usePaperDrawdown } from "@/lib/hooks";
import { formatVND, formatCompactVND } from "@/lib/format";
import { EquityCurveChart } from "@/components/shared/equity-curve-chart";

export function PTEquityChart() {
  const { data: equityCurve, isLoading: loadingEquity } = usePaperEquityCurve();
  const { data: drawdown, isLoading: loadingDrawdown } = usePaperDrawdown();

  const isLoading = loadingEquity || loadingDrawdown;

  const chartData = useMemo(
    () =>
      equityCurve?.data?.map((d) => ({
        date: d.date,
        value: d.cumulative_pnl,
      })) ?? [],
    [equityCurve],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Đường cong vốn</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-80 w-full rounded-lg" />
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu đường cong vốn.
            </p>
          </div>
        ) : (
          <>
            <EquityCurveChart
              data={chartData}
              label="Tích lũy"
              height={320}
              formatValue={(v) => `${formatVND(v)} ₫`}
              formatYAxis={formatCompactVND}
            />

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
