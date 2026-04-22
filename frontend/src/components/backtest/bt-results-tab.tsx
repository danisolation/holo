"use client";

import { useMemo } from "react";
import {
  Target,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Hash,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useBacktestLatest,
  useBacktestBenchmark,
  useBacktestAnalytics,
} from "@/lib/hooks";
import type {
  BenchmarkComparisonResponse,
  BacktestAnalyticsResponse,
} from "@/lib/api";
import { formatVND } from "@/lib/format";
import { EquityCurveChart } from "@/components/shared/equity-curve-chart";

// --- Equity Curve Card ---

function EquityCurveCard({
  benchmark,
  isLoading,
}: {
  benchmark: BenchmarkComparisonResponse | undefined;
  isLoading: boolean;
}) {
  const chartData = useMemo(
    () =>
      benchmark?.data?.map((d) => ({ date: d.date, value: d.ai_return_pct })) ??
      [],
    [benchmark],
  );

  const benchmarkChartData = useMemo(
    () =>
      benchmark?.data
        ?.filter((d) => d.vnindex_return_pct != null)
        .map((d) => ({ date: d.date, value: d.vnindex_return_pct! })) ?? [],
    [benchmark],
  );

  if (isLoading) {
    return <Skeleton className="h-[460px] rounded-xl" />;
  }

  if (!benchmark?.data?.length) {
    return (
      <Card data-testid="bt-equity-chart">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">
            Đường cong vốn — AI vs VN-Index
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-80">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu đường cong vốn.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="bt-equity-chart">
      <CardHeader>
        <CardTitle className="text-lg font-semibold">
          Đường cong vốn — AI vs VN-Index
        </CardTitle>
      </CardHeader>
      <CardContent>
        <EquityCurveChart
          data={chartData}
          benchmarkData={benchmarkChartData}
          label="AI Strategy"
          benchmarkLabel="VN-Index"
          height={360}
          formatValue={(v) => `${v.toFixed(2)}%`}
          formatYAxis={(v) => `${v.toFixed(0)}%`}
        />

        {/* Benchmark summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">AI Return</p>
              <p
                className={`text-xl font-bold font-mono ${
                  benchmark.ai_total_return_pct >= 0
                    ? "text-[#26a69a]"
                    : "text-[#ef5350]"
                }`}
              >
                {benchmark.ai_total_return_pct >= 0 ? "+" : ""}
                {benchmark.ai_total_return_pct.toFixed(2)}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">VN-Index Return</p>
              <p className="text-xl font-bold font-mono">
                {benchmark.vnindex_total_return_pct != null
                  ? `${benchmark.vnindex_total_return_pct >= 0 ? "+" : ""}${benchmark.vnindex_total_return_pct.toFixed(2)}%`
                  : "N/A"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Outperformance</p>
              <p
                className={`text-xl font-bold font-mono ${
                  benchmark.outperformance_pct != null &&
                  benchmark.outperformance_pct >= 0
                    ? "text-[#26a69a]"
                    : "text-[#ef5350]"
                }`}
              >
                {benchmark.outperformance_pct != null
                  ? `${benchmark.outperformance_pct >= 0 ? "+" : ""}${benchmark.outperformance_pct.toFixed(2)}%`
                  : "N/A"}
              </p>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Stats Cards ---

function StatsCards({
  analytics,
  isLoading,
}: {
  analytics: BacktestAnalyticsResponse | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div
        data-testid="bt-stats-cards"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!analytics) return null;

  const s = analytics.summary;
  const pnlPositive = s.total_pnl >= 0;
  const sharpeColor =
    s.sharpe_ratio >= 1
      ? "text-[#26a69a]"
      : s.sharpe_ratio >= 0
        ? "text-[#f59e0b]"
        : "text-[#ef5350]";

  return (
    <div
      data-testid="bt-stats-cards"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
    >
      {/* Win Rate */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tỷ lệ thắng</CardTitle>
          <Target className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{s.win_rate.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            {s.wins}W / {s.losses}L trên {s.total_trades} lệnh
          </p>
        </CardContent>
      </Card>

      {/* Total P&L */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tổng P&L</CardTitle>
          {pnlPositive ? (
            <TrendingUp className="size-4 text-[#26a69a]" />
          ) : (
            <TrendingDown className="size-4 text-[#ef5350]" />
          )}
        </CardHeader>
        <CardContent>
          <div
            className={`text-2xl font-bold font-mono ${pnlPositive ? "text-[#26a69a]" : "text-[#ef5350]"}`}
          >
            {pnlPositive ? "+" : ""}
            {formatVND(s.total_pnl)} ₫
          </div>
          <p className="text-xs text-muted-foreground">
            {pnlPositive ? "+" : ""}
            {s.total_pnl_pct.toFixed(2)}% so với vốn
          </p>
        </CardContent>
      </Card>

      {/* Max Drawdown */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
          <TrendingDown className="size-4 text-[#ef5350]" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold font-mono text-[#ef5350]">
            {formatVND(s.max_drawdown)} ₫
          </div>
          <p className="text-xs text-muted-foreground">
            {s.max_drawdown_pct.toFixed(2)}%
          </p>
        </CardContent>
      </Card>

      {/* Sharpe Ratio */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
          <BarChart3 className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold font-mono ${sharpeColor}`}>
            {s.sharpe_ratio.toFixed(2)}
          </div>
          <p className="text-xs text-muted-foreground">
            {s.sharpe_ratio >= 1
              ? "Tốt"
              : s.sharpe_ratio >= 0
                ? "Trung bình"
                : "Kém"}
          </p>
        </CardContent>
      </Card>

      {/* Total Trades */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tổng lệnh</CardTitle>
          <Hash className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{s.total_trades}</div>
          <p className="text-xs text-muted-foreground">Trong kỳ backtest</p>
        </CardContent>
      </Card>
    </div>
  );
}

// --- BTResultsTab ---

export function BTResultsTab() {
  const { data: latestRun, isLoading: loadingRun } =
    useBacktestLatest(false);

  const runId =
    latestRun?.status === "completed" ? latestRun.id : undefined;

  const { data: benchmark, isLoading: loadingBench } =
    useBacktestBenchmark(runId);
  const { data: analytics, isLoading: loadingAnalytics } =
    useBacktestAnalytics(runId);

  if (loadingRun) {
    return (
      <div className="space-y-6 mt-4">
        <Skeleton className="h-[460px] rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!latestRun || latestRun.status !== "completed") {
    return (
      <div className="py-8 text-center text-muted-foreground text-sm">
        Chưa có kết quả backtest. Vui lòng chạy backtest từ tab Cấu hình.
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-4">
      <EquityCurveCard benchmark={benchmark} isLoading={loadingBench} />
      <StatsCards analytics={analytics} isLoading={loadingAnalytics} />
    </div>
  );
}
