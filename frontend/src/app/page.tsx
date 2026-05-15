"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  RefreshCw,
  Compass,
  Sparkles,
  Wallet,
  Target,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Heatmap } from "@/components/heatmap";
import { SectorAIPanel } from "@/components/sector-ai-panel";
import {
  useMarketOverview,
  useWatchlist,
  useAnalysisCoverage,
  useSimulatorPortfolio,
  usePendingSignals,
} from "@/lib/hooks";

function formatVnd(value: number | undefined | null): string {
  if (value == null) return "—";
  const millions = value / 1_000_000;
  return new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(millions) + "M ₫";
}

function formatPnlPct(value: number | undefined | null): string {
  if (value == null) return "";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export default function Home() {
  const { data, isLoading, error, refetch } = useMarketOverview();
  const { data: watchlistData } = useWatchlist();
  const { data: coverage } = useAnalysisCoverage();
  const { data: portfolio } = useSimulatorPortfolio();
  const { data: signals } = usePendingSignals();

  const totalTickers = data?.length ?? 0;
  const gainers = data?.filter((t) => t.change_pct != null && t.change_pct > 0).length ?? 0;
  const losers = data?.filter((t) => t.change_pct != null && t.change_pct < 0).length ?? 0;
  const unchanged = totalTickers - gainers - losers;

  const topMovers = useMemo(() => {
    if (!data) return null;
    const gainersList = data.filter((t) => t.change_pct != null && t.change_pct > 0);
    const losersList = data.filter((t) => t.change_pct != null && t.change_pct < 0);
    const topGainers = [...gainersList]
      .sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))
      .slice(0, 5);
    const topLosers = [...losersList]
      .sort((a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0))
      .slice(0, 5);
    return { topGainers, topLosers };
  }, [data]);

  const watchlistHeatmapData = useMemo(() => {
    if (!data || !watchlistData) return [];
    const marketMap = new Map(data.map((t) => [t.symbol, t]));
    return watchlistData
      .map((w) => {
        const market = marketMap.get(w.symbol);
        if (!market) return null;
        // Override sector with user's sector_group, fallback to ICB sector from market data
        return { ...market, sector: w.sector_group ?? market.sector ?? "Khác" };
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);
  }, [data, watchlistData]);

  const subtitle = watchlistData && watchlistData.length > 0
    ? `Bản đồ nhiệt ${watchlistData.length} mã trong danh mục, phân nhóm theo ngành`
    : "Thêm mã vào danh mục để xem bản đồ nhiệt theo ngành";

  const pnlColor = (portfolio?.total_pnl ?? 0) >= 0 ? "text-trading-bull" : "text-trading-bear";

  return (
    <>
      {/* Page title */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold tracking-tight">
          Tổng quan thị trường
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {subtitle}
        </p>
      </div>

      {/* Row 1 — Key Metrics */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <Card className="mb-4">
          <CardContent className="flex items-center justify-between py-4">
            <p className="text-sm text-destructive">
              Không thể tải dữ liệu thị trường
            </p>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1 text-destructive">
              <RefreshCw className="size-3" />
              Thử lại
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <Wallet className="size-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">
                  {portfolio?.total_equity != null ? formatVnd(portfolio.total_equity) : "—"}
                </p>
                {portfolio?.total_pnl_pct != null && (
                  <p className={`text-xs font-medium ${pnlColor}`}>
                    {formatPnlPct(portfolio.total_pnl_pct)}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">Danh mục</p>
              </div>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <Target className={`size-8 ${pnlColor}`} />
              <div>
                <p className={`text-2xl font-bold ${pnlColor}`}>
                  {portfolio?.total_pnl != null ? formatVnd(portfolio.total_pnl) : "—"}
                </p>
                <p className="text-xs text-muted-foreground">Lãi/Lỗ hôm nay</p>
              </div>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <Sparkles className="size-8 text-violet-500" />
              <div>
                <p className="text-2xl font-bold">
                  {coverage ? `${coverage.analyzed_today}/${coverage.total_watchlist}` : "—"}
                </p>
                <p className="text-xs text-muted-foreground">AI phân tích</p>
              </div>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <BarChart3 className="size-8 text-muted-foreground" />
              <div>
                <p className="text-2xl font-bold">
                  <span className="text-trading-bull">{gainers}</span>
                  <span className="text-muted-foreground mx-0.5">↑</span>
                  <span className="text-muted-foreground">/</span>
                  <span className="text-muted-foreground mx-0.5"> </span>
                  <span className="text-trading-bear">{losers}</span>
                  <span className="text-muted-foreground mx-0.5">↓</span>
                </p>
                <p className="text-xs text-muted-foreground">Thị trường</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Row 2 — AI Signals + Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-violet-500">
              <Sparkles className="size-4" />
              Tín hiệu AI mới
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {!signals || signals.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Không có tín hiệu mới
              </p>
            ) : (
              signals.slice(0, 3).map((s) => (
                <div
                  key={s.daily_pick_id}
                  className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm">
                      {s.ticker_symbol}
                    </span>
                    <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-500">
                      #{s.rank ?? "—"}
                    </span>
                  </div>
                  <span className="font-mono text-sm text-muted-foreground">
                    {s.entry_price != null
                      ? new Intl.NumberFormat("vi-VN").format(s.entry_price) + " ₫"
                      : "—"}
                  </span>
                </div>
              ))
            )}
            <div className="pt-1">
              <Link
                href="/simulator"
                className="text-xs text-violet-500 hover:underline"
              >
                Xem tất cả tín hiệu →
              </Link>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="size-4 text-muted-foreground" />
              Thống kê nhanh
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Tổng mã</span>
              <span className="font-mono font-bold text-sm">{totalTickers}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Đứng giá</span>
              <span className="font-mono font-bold text-sm">{unchanged}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Danh mục theo dõi</span>
              <span className="font-mono font-bold text-sm">{watchlistData?.length ?? 0} mã</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Heatmap */}
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-32" />
          <div className="grid grid-cols-6 md:grid-cols-10 gap-1">
            {Array.from({ length: 60 }).map((_, i) => (
              <Skeleton key={i} className="h-[52px] rounded-md" />
            ))}
          </div>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-destructive font-medium mb-2">
              Không thể tải dữ liệu thị trường
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              {error instanceof Error ? error.message : "Lỗi không xác định"}
            </p>
            <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1 text-destructive">
              <RefreshCw className="size-3" />
              Thử lại
            </Button>
          </CardContent>
        </Card>
      ) : watchlistHeatmapData.length > 0 ? (
        <Heatmap data={watchlistHeatmapData} />
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Compass className="size-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground font-medium mb-1">
              Chưa có mã trong danh mục
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Thêm mã vào danh mục theo dõi để xem bản đồ nhiệt theo nhóm ngành.
            </p>
            <div className="flex gap-2">
              <Link
                href="/watchlist"
                className="inline-flex items-center justify-center rounded-[min(var(--radius-md),12px)] border border-input bg-background px-2.5 h-7 text-[0.8rem] font-medium shadow-xs hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                Mở danh mục
              </Link>
              <Link
                href="/discovery"
                className="inline-flex items-center justify-center rounded-[min(var(--radius-md),12px)] border border-input bg-background px-2.5 h-7 text-[0.8rem] font-medium shadow-xs hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                Khám phá cổ phiếu
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Movers — merged from /dashboard */}
      {topMovers && (
        <section className="mt-8">
          <h3 className="text-lg font-semibold mb-3">Top biến động</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Top Gainers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-trading-bull">
                  <TrendingUp className="size-4" />
                  Top tăng
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {topMovers.topGainers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã tăng
                  </p>
                ) : (
                  topMovers.topGainers.map((t) => (
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
                      <span className="font-mono text-sm text-trading-bull">
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
                <CardTitle className="flex items-center gap-2 text-trading-bear">
                  <TrendingDown className="size-4" />
                  Top giảm
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {topMovers.topLosers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã giảm
                  </p>
                ) : (
                  topMovers.topLosers.map((t) => (
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
                      <span className="font-mono text-sm text-trading-bear">
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

      {/* AI Sector Intelligence */}
      <SectorAIPanel />
    </>
  );
}
