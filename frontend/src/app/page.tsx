"use client";

import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Heatmap } from "@/components/heatmap";
import { ExchangeFilter } from "@/components/exchange-filter";
import { useExchangeStore } from "@/lib/store";
import { useMarketOverview } from "@/lib/hooks";

export default function Home() {
  const { exchange } = useExchangeStore();
  const { data, isLoading, error } = useMarketOverview(exchange);

  const totalTickers = data?.length ?? 0;
  const gainers = data?.filter((t) => t.change_pct != null && t.change_pct > 0).length ?? 0;
  const losers = data?.filter((t) => t.change_pct != null && t.change_pct < 0).length ?? 0;
  const unchanged = totalTickers - gainers - losers;

  const subtitle = exchange === "all" || !exchange
    ? "Bản đồ nhiệt toàn thị trường theo biến động giá trong ngày"
    : `Bản đồ nhiệt sàn ${exchange} theo biến động giá trong ngày`;

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

      {/* Exchange filter */}
      <div className="mb-6">
        <ExchangeFilter />
      </div>

      {/* Market Stats */}
      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
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
            <p className="text-sm text-muted-foreground">
              {error instanceof Error ? error.message : "Lỗi không xác định"}
            </p>
          </CardContent>
        </Card>
      ) : data ? (
        <Heatmap data={data} exchange={exchange} />
      ) : null}
    </>
  );
}
