"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperTimeframe } from "@/lib/hooks";
import { formatVND } from "@/lib/format";

const TIMEFRAME_LABELS: Record<string, string> = {
  swing: "Swing (ngắn hạn)",
  position: "Position (dài hạn)",
};

export function PTTimeframeCompare() {
  const { data, isLoading } = usePaperTimeframe();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">So sánh Timeframe</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-40 w-full rounded-lg" />
        ) : !data?.length ? (
          <div className="flex items-center justify-center h-40">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu so sánh timeframe.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.map((item) => (
              <Card key={item.timeframe}>
                <CardContent className="pt-4 space-y-3">
                  <p className="text-base font-semibold">
                    {TIMEFRAME_LABELS[item.timeframe] ?? item.timeframe}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Tỷ lệ thắng:</span>
                    <Badge variant={item.win_rate >= 50 ? "default" : "destructive"}>
                      {item.win_rate.toFixed(1)}%
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">Tổng lệnh</p>
                      <p className="font-semibold">{item.total_trades}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">W / L</p>
                      <p className="font-semibold">
                        <span className="text-[#26a69a]">{item.wins}</span>
                        {" / "}
                        <span className="text-[#ef5350]">{item.losses}</span>
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Tổng P&L</p>
                      <p
                        className={`font-semibold font-mono ${
                          item.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                        }`}
                      >
                        {item.total_pnl >= 0 ? "+" : ""}
                        {formatVND(item.total_pnl)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">TB P&L</p>
                      <p
                        className={`font-semibold font-mono ${
                          item.avg_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                        }`}
                      >
                        {item.avg_pnl >= 0 ? "+" : ""}
                        {formatVND(item.avg_pnl)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
