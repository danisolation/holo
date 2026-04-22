"use client";

import {
  Target,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Hash,
} from "lucide-react";
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

// --- Equity Curve Tooltip ---

interface EquityTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: {
      date: string;
      ai_return_pct: number;
      vnindex_return_pct: number | null;
    };
  }>;
  label?: string;
}

function EquityTooltip({ active, payload, label }: EquityTooltipProps) {
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
        AI:{" "}
        <span
          className={
            point.ai_return_pct >= 0 ? "text-[#3b82f6]" : "text-[#ef5350]"
          }
        >
          {point.ai_return_pct >= 0 ? "+" : ""}
          {point.ai_return_pct.toFixed(2)}%
        </span>
      </p>
      <p className="text-sm font-semibold font-mono">
        VN-Index:{" "}
        <span className="text-[#f59e0b]">
          {point.vnindex_return_pct != null
            ? `${point.vnindex_return_pct >= 0 ? "+" : ""}${point.vnindex_return_pct.toFixed(2)}%`
            : "N/A"}
        </span>
      </p>
    </div>
  );
}

// --- Equity Curve Card ---

function EquityCurveCard({
  benchmark,
  isLoading,
}: {
  benchmark: BenchmarkComparisonResponse | undefined;
  isLoading: boolean;
}) {
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
        <ResponsiveContainer width="100%" height={360}>
          <AreaChart data={benchmark.data}>
            <defs>
              <linearGradient id="aiGradient" x1="0" y1="0" x2="0" y2="1">
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
              width={50}
              tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            />
            <Tooltip content={<EquityTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey="ai_return_pct"
              name="AI Strategy"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#aiGradient)"
            />
            <Line
              type="monotone"
              dataKey="vnindex_return_pct"
              name="VN-Index"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>

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
