"use client";

import { useMemo } from "react";
import Link from "next/link";
import { TrendingUp, TrendingDown, BarChart3, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Heatmap } from "@/components/heatmap";
import { useMarketOverview, useWatchlist } from "@/lib/hooks";

export default function Home() {
  const { data, isLoading, error, refetch } = useMarketOverview();
  const { data: watchlistData } = useWatchlist();

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

      {/* Market Stats */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <Card className="mb-6">
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <BarChart3 className="size-8 text-muted-foreground" />
              <div>
                <p className="text-2xl font-bold">{totalTickers}</p>
                <p className="text-xs text-muted-foreground">Tổng mã</p>
              </div>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <TrendingUp className="size-8 text-[#26a69a]" />
              <div>
                <p className="text-2xl font-bold text-[#26a69a]">{gainers}</p>
                <p className="text-xs text-muted-foreground">Tăng giá</p>
              </div>
            </CardContent>
          </Card>
          <Card size="sm">
            <CardContent className="flex items-center gap-3">
              <TrendingDown className="size-8 text-[#ef5350]" />
              <div>
                <p className="text-2xl font-bold text-[#ef5350]">{losers}</p>
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
                <p className="text-2xl font-bold">{unchanged}</p>
                <p className="text-xs text-muted-foreground">Đứng giá</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
            <p className="text-muted-foreground font-medium mb-2">
              Chưa có mã trong danh mục
            </p>
            <p className="text-sm text-muted-foreground">
              Thêm mã vào danh mục theo dõi để xem bản đồ nhiệt theo nhóm ngành.
            </p>
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
                <CardTitle className="flex items-center gap-2 text-[#26a69a]">
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
    </>
  );
}
