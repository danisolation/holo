"use client";

import { usePickPerformance } from "@/lib/hooks";
import { formatVND } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function PickPerformanceCards() {
  const { data: stats, isLoading, isError } = usePickPerformance();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
      </div>
    );
  }

  // Graceful degradation: show dashes on error
  if (isError || !stats) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card aria-label="Tỷ lệ thắng: —">
          <CardContent>
            <p className="text-xs text-muted-foreground">Tỷ lệ thắng</p>
            <p className="font-mono text-2xl font-bold text-muted-foreground">—</p>
          </CardContent>
        </Card>
        <Card aria-label="Lãi/lỗ thực hiện: —">
          <CardContent>
            <p className="text-xs text-muted-foreground">Lãi/lỗ thực hiện</p>
            <p className="font-mono text-2xl font-bold text-muted-foreground">—</p>
          </CardContent>
        </Card>
        <Card aria-label="TB tỷ lệ R:R: —">
          <CardContent>
            <p className="text-xs text-muted-foreground">TB tỷ lệ R:R</p>
            <p className="font-mono text-2xl font-bold text-muted-foreground">—</p>
          </CardContent>
        </Card>
        <Card aria-label="Chuỗi hiện tại: —">
          <CardContent>
            <p className="text-xs text-muted-foreground">Chuỗi hiện tại</p>
            <p className="font-mono text-2xl font-bold text-muted-foreground">—</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Win rate color
  const winRateColor =
    stats.win_rate > 50
      ? "text-[#26a69a]"
      : stats.win_rate < 50
        ? "text-[#ef5350]"
        : "text-muted-foreground";

  // P&L color and formatting
  const pnl = stats.total_pnl;
  const pnlColor =
    pnl > 0
      ? "text-[#26a69a]"
      : pnl < 0
        ? "text-[#ef5350]"
        : "text-muted-foreground";
  const pnlDisplay =
    pnl > 0
      ? `+${formatVND(pnl)} VND`
      : pnl < 0
        ? `-${formatVND(Math.abs(pnl))} VND`
        : "0 VND";

  // Streak display
  const streak = stats.current_streak;
  let streakColor = "text-muted-foreground";
  let streakDisplay = "— Chưa có";
  if (streak > 0) {
    streakColor = "text-[#26a69a]";
    streakDisplay = `🔥 ${streak} thắng`;
  } else if (streak < 0) {
    streakColor = "text-[#ef5350]";
    streakDisplay = `❄️ ${Math.abs(streak)} thua`;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <Card aria-label={`Tỷ lệ thắng: ${stats.win_rate.toFixed(1)} phần trăm`}>
        <CardContent>
          <p className="text-xs text-muted-foreground">Tỷ lệ thắng</p>
          <p className={`font-mono text-2xl font-bold ${winRateColor}`}>
            {stats.win_rate.toFixed(1)}%
          </p>
        </CardContent>
      </Card>

      <Card aria-label={`Lãi/lỗ thực hiện: ${pnlDisplay}`}>
        <CardContent>
          <p className="text-xs text-muted-foreground">Lãi/lỗ thực hiện</p>
          <p className={`font-mono text-2xl font-bold ${pnlColor}`}>
            {pnlDisplay}
          </p>
        </CardContent>
      </Card>

      <Card aria-label={`TB tỷ lệ R:R: 1:${stats.avg_risk_reward.toFixed(1)}`}>
        <CardContent>
          <p className="text-xs text-muted-foreground">TB tỷ lệ R:R</p>
          <p className="font-mono text-2xl font-bold">
            1:{stats.avg_risk_reward.toFixed(1)}
          </p>
        </CardContent>
      </Card>

      <Card aria-label={`Chuỗi hiện tại: ${streakDisplay}`}>
        <CardContent>
          <p className="text-xs text-muted-foreground">Chuỗi hiện tại</p>
          <p className={`font-mono text-2xl font-bold ${streakColor}`}>
            {streak > 0 && <span aria-hidden="true">🔥 </span>}
            {streak < 0 && <span aria-hidden="true">❄️ </span>}
            {streak > 0
              ? `${streak} thắng`
              : streak < 0
                ? `${Math.abs(streak)} thua`
                : "— Chưa có"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
