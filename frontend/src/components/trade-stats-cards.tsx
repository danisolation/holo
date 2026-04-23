"use client";

import { useTradeStats } from "@/lib/hooks";
import { formatVND } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function TradeStatsCards() {
  const { data: stats, isLoading } = useTradeStats();

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-20 rounded-xl" />
      </div>
    );
  }

  const pnl = stats.realized_net_pnl;
  const pnlColor =
    pnl > 0
      ? "text-[#26a69a]"
      : pnl < 0
        ? "text-[#ef5350]"
        : "text-muted-foreground";
  const pnlPrefix = pnl > 0 ? "+" : pnl < 0 ? "-" : "";
  const pnlDisplay = `${pnlPrefix}${formatVND(Math.abs(pnl))} VND`;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Card>
        <CardContent>
          <p className="text-xs text-muted-foreground">Tổng giao dịch</p>
          <p className="font-mono text-2xl font-bold">{stats.total_trades}</p>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <p className="text-xs text-muted-foreground">Lãi/lỗ thực hiện</p>
          <p className={`font-mono text-2xl font-bold ${pnlColor}`}>
            {pnlDisplay}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <p className="text-xs text-muted-foreground">Vị thế đang mở</p>
          <p className="font-mono text-2xl font-bold">
            {stats.open_positions}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
