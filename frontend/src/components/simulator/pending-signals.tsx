"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { usePendingSignals, useExecuteSignals, useSkipSignals } from "@/lib/hooks";
import type { PendingSignalResponse } from "@/lib/api";

function formatPrice(v: number | null): string {
  if (v == null) return "—";
  return v.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

export function PendingSignals() {
  const { data: signals, isLoading } = usePendingSignals();
  const executeMutation = useExecuteSignals();
  const skipMutation = useSkipSignals();

  function handleExecute(pickId: number) {
    executeMutation.mutate([pickId]);
  }

  function handleSkip(pickId: number) {
    skipMutation.mutate([pickId]);
  }

  function handleExecuteAll() {
    if (!signals || signals.length === 0) return;
    const ids = signals.map((s: PendingSignalResponse) => s.daily_pick_id);
    executeMutation.mutate(ids);
  }

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        Đang tải tín hiệu AI...
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {!signals || signals.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              Không có tín hiệu AI mới
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">
              Tín hiệu AI chờ xử lý ({signals.length})
            </CardTitle>
            <Button
              size="sm"
              onClick={handleExecuteAll}
              disabled={executeMutation.isPending}
              className="bg-trading-bull hover:bg-trading-bull/90 text-white"
            >
              {executeMutation.isPending
                ? "Đang thực hiện..."
                : "Thực hiện tất cả"}
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {signals.map((signal: PendingSignalResponse) => (
              <div
                key={signal.daily_pick_id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">
                      {signal.ticker_symbol}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {signal.ticker_name}
                    </span>
                    {signal.rank && (
                      <Badge variant="secondary" className="text-xs">
                        #{signal.rank}
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>Ngày: {signal.pick_date}</span>
                    <span>Giá vào: {formatPrice(signal.entry_price)}</span>
                    <span>SL: {formatPrice(signal.stop_loss)}</span>
                    <span>TP1: {formatPrice(signal.take_profit_1)}</span>
                    <span>Điểm: {signal.composite_score.toFixed(1)}</span>
                    {signal.position_size_shares && (
                      <span>SL cổ: {signal.position_size_shares}</span>
                    )}
                  </div>
                  {signal.explanation && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2 hover:line-clamp-none cursor-pointer transition-all">
                      💡 {signal.explanation}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    size="sm"
                    onClick={() => handleExecute(signal.daily_pick_id)}
                    disabled={
                      executeMutation.isPending || skipMutation.isPending
                    }
                    className="bg-trading-bull hover:bg-trading-bull/90 text-white"
                  >
                    Thực hiện
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSkip(signal.daily_pick_id)}
                    disabled={
                      executeMutation.isPending || skipMutation.isPending
                    }
                  >
                    Bỏ qua
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
