"use client";

import { TrendingUp, TrendingDown, Target, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperAnalyticsSummary } from "@/lib/hooks";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

export function PTOverviewTab() {
  const { data, isLoading, error } = usePaperAnalyticsSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-8 text-center text-muted-foreground text-sm">
        Không thể tải dữ liệu phân tích. Thử lại sau.
      </div>
    );
  }

  const pnlPositive = data.total_pnl >= 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
      {/* Win Rate */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tỷ lệ thắng</CardTitle>
          <Target className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.win_rate.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            {data.wins}W / {data.losses}L trên {data.total_trades} lệnh
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
          <div className={`text-2xl font-bold font-mono ${pnlPositive ? "text-[#26a69a]" : "text-[#ef5350]"}`}>
            {pnlPositive ? "+" : ""}{formatVND(data.total_pnl)}
          </div>
          <p className="text-xs text-muted-foreground">
            {pnlPositive ? "+" : ""}{data.total_pnl_pct.toFixed(2)}% so với vốn
          </p>
        </CardContent>
      </Card>

      {/* Trade Count */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tổng lệnh</CardTitle>
          <BarChart3 className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.total_trades}</div>
          <p className="text-xs text-muted-foreground">
            Đã đóng và đang mở
          </p>
        </CardContent>
      </Card>

      {/* Avg P&L per Trade */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">TB P&L/lệnh</CardTitle>
          <TrendingUp className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold font-mono ${data.avg_pnl_per_trade >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}`}>
            {data.avg_pnl_per_trade >= 0 ? "+" : ""}{formatVND(data.avg_pnl_per_trade)}
          </div>
          <p className="text-xs text-muted-foreground">
            Trung bình mỗi lệnh đã đóng
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
