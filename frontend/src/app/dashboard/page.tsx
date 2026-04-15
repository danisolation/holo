"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Brain,
  Minus,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useMarketOverview, useAnalysisSummary } from "@/lib/hooks";
import { useWatchlistStore } from "@/lib/store";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

/** Individual ticker summary card — fetches its own analysis */
function TickerSummaryCard({ symbol }: { symbol: string }) {
  const { data, isLoading } = useAnalysisSummary(symbol);
  const combined = data?.combined;

  if (isLoading) return <Skeleton className="h-32 rounded-xl" />;

  if (!combined) {
    return (
      <Card size="sm">
        <CardContent>
          <div className="flex items-center justify-between">
            <Link
              href={`/ticker/${symbol}`}
              className="font-mono font-bold hover:underline"
            >
              {symbol}
            </Link>
            <span className="text-xs text-muted-foreground">
              Chưa có phân tích
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const key = combined.signal.toLowerCase().replace(/\s+/g, "_");
  const isBuy = ["buy", "strong_buy", "bullish"].includes(key);
  const isSell = ["sell", "strong_sell", "bearish"].includes(key);

  return (
    <Card size="sm">
      <CardContent className="space-y-2">
        <div className="flex items-center justify-between">
          <Link
            href={`/ticker/${symbol}`}
            className="font-mono font-bold hover:underline"
          >
            {symbol}
          </Link>
          <Badge
            variant="secondary"
            className={
              isBuy
                ? "text-[#26a69a] bg-[#26a69a]/10 gap-1"
                : isSell
                  ? "text-[#ef5350] bg-[#ef5350]/10 gap-1"
                  : "gap-1"
            }
          >
            {isBuy ? (
              <TrendingUp className="size-3" />
            ) : isSell ? (
              <TrendingDown className="size-3" />
            ) : (
              <Minus className="size-3" />
            )}
            {combined.signal.toUpperCase().replace(/_/g, " ")}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Điểm:</span>
          <span className="text-sm font-bold">{combined.score}/10</span>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2">
          {combined.reasoning}
        </p>
      </CardContent>
    </Card>
  );
}

const PIE_COLORS: Record<string, string> = {
  "Tăng": "#26a69a",
  "Giảm": "#ef5350",
  "Đứng giá": "#888888",
};

export default function DashboardPage() {
  const { watchlist } = useWatchlistStore();
  const { data: marketData, isLoading } = useMarketOverview();

  const stats = useMemo(() => {
    if (!marketData) return null;

    const gainers = marketData.filter(
      (t) => t.change_pct != null && t.change_pct > 0,
    );
    const losers = marketData.filter(
      (t) => t.change_pct != null && t.change_pct < 0,
    );
    const unchanged = marketData.length - gainers.length - losers.length;

    const topGainers = [...gainers]
      .sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))
      .slice(0, 5);
    const topLosers = [...losers]
      .sort((a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0))
      .slice(0, 5);

    const pieData = [
      { name: "Tăng", value: gainers.length },
      { name: "Giảm", value: losers.length },
      { name: "Đứng giá", value: unchanged },
    ].filter((d) => d.value > 0);

    return {
      gainers: gainers.length,
      losers: losers.length,
      unchanged,
      topGainers,
      topLosers,
      pieData,
    };
  }, [marketData]);

  return (
    <div className="space-y-8">
      {/* Page title */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Bảng điều khiển</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Tổng quan danh mục và thị trường
        </p>
      </div>

      {/* Section 1: Watchlist Summary */}
      <section>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Brain className="size-5" />
          Danh mục theo dõi
          {watchlist.length > 0 && (
            <Badge variant="secondary">{watchlist.length}</Badge>
          )}
        </h3>
        {watchlist.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground text-sm">
              Chưa có mã nào trong danh mục theo dõi.
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {watchlist.map((symbol) => (
              <TickerSummaryCard key={symbol} symbol={symbol} />
            ))}
          </div>
        )}
      </section>

      {/* Section 2: Market Stats */}
      <section>
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <BarChart3 className="size-5" />
          Thống kê thị trường
        </h3>
        {isLoading || !stats ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Card size="sm">
              <CardContent className="flex items-center gap-3">
                <TrendingUp className="size-8 text-[#26a69a]" />
                <div>
                  <p className="text-2xl font-bold text-[#26a69a]">
                    {stats.gainers}
                  </p>
                  <p className="text-xs text-muted-foreground">Tăng giá</p>
                </div>
              </CardContent>
            </Card>
            <Card size="sm">
              <CardContent className="flex items-center gap-3">
                <TrendingDown className="size-8 text-[#ef5350]" />
                <div>
                  <p className="text-2xl font-bold text-[#ef5350]">
                    {stats.losers}
                  </p>
                  <p className="text-xs text-muted-foreground">Giảm giá</p>
                </div>
              </CardContent>
            </Card>
            <Card size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="size-8 rounded-full bg-muted flex items-center justify-center text-sm font-bold text-muted-foreground">
                  =
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.unchanged}</p>
                  <p className="text-xs text-muted-foreground">Đứng giá</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </section>

      {/* Section 3: Signal Distribution Pie Chart */}
      {stats && stats.pieData.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Phân bổ tăng/giảm</h3>
          <Card>
            <CardContent className="py-4">
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="value"
                      nameKey="name"
                      paddingAngle={2}
                    >
                      {stats.pieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={PIE_COLORS[entry.name] ?? "#888"}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "0.5rem",
                        color: "hsl(var(--popover-foreground))",
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Section 4: Top Movers */}
      {stats && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Top biến động</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Top Gainers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#26a69a]">
                  <TrendingUp className="size-4" />
                  Top tăng
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {stats.topGainers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã tăng
                  </p>
                ) : (
                  stats.topGainers.map((t) => (
                    <Link
                      key={t.symbol}
                      href={`/ticker/${t.symbol}`}
                      className="flex items-center justify-between py-1.5 rounded-md px-2 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm">
                          {t.symbol}
                        </span>
                        <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                          {t.name}
                        </span>
                      </div>
                      <span className="font-mono text-sm text-[#26a69a]">
                        +{(t.change_pct ?? 0).toFixed(2)}%
                      </span>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Top Losers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#ef5350]">
                  <TrendingDown className="size-4" />
                  Top giảm
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {stats.topLosers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã giảm
                  </p>
                ) : (
                  stats.topLosers.map((t) => (
                    <Link
                      key={t.symbol}
                      href={`/ticker/${t.symbol}`}
                      className="flex items-center justify-between py-1.5 rounded-md px-2 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm">
                          {t.symbol}
                        </span>
                        <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                          {t.name}
                        </span>
                      </div>
                      <span className="font-mono text-sm text-[#ef5350]">
                        {(t.change_pct ?? 0).toFixed(2)}%
                      </span>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      )}
    </div>
  );
}
