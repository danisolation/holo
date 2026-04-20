"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperTrades } from "@/lib/hooks";

const STATUS_LABEL: Record<string, string> = {
  closed_tp2: "TP2",
  closed_sl: "SL",
  closed_timeout: "Timeout",
  closed_manual: "Manual",
  active: "Mở",
  pending: "Chờ",
  partial_tp: "TP1",
};

export function PTSignalOutcomes({ symbol }: { symbol: string }) {
  const { data, isLoading } = usePaperTrades({ symbol, limit: 10 });

  if (isLoading) return <Skeleton className="h-32 rounded-xl" />;
  if (!data?.trades.length) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Kết quả tín hiệu gần đây</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {data.trades.map((trade) => {
            let icon = "⏳";
            if (trade.realized_pnl != null) {
              icon = trade.realized_pnl > 0 ? "✅" : "❌";
            }

            return (
              <div
                key={trade.id}
                className="flex items-center justify-between text-sm"
              >
                <span className="font-mono text-xs text-muted-foreground w-20">
                  {trade.signal_date}
                </span>
                <Badge
                  variant="secondary"
                  className={
                    trade.direction === "long"
                      ? "text-[#26a69a] bg-[#26a69a]/10"
                      : "text-[#ef5350] bg-[#ef5350]/10"
                  }
                >
                  {trade.direction.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {STATUS_LABEL[trade.status] ?? trade.status}
                </span>
                <span className="text-base">{icon}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
