"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreBar } from "@/components/analysis-card";
import { cn } from "@/lib/utils";
import type { TickerTradingSignal } from "@/lib/api";

const fmt = (v: number) => Math.round(v).toLocaleString("vi-VN");

const TIMEFRAME_LABELS: Record<string, string> = {
  swing: "Swing (3-15 ngày)",
  position: "Position (vài tuần+)",
};

/** Single-direction trading plan panel — shows recommended direction only. */
interface TradingPlanPanelProps {
  data: TickerTradingSignal;
  symbol: string;
}

export function TradingPlanPanel({ data }: TradingPlanPanelProps) {
  const isLong = data.recommended_direction === "long";
  const borderColor = isLong ? "border-[#26a69a]" : "border-[#ef5350]";
  const bgTint = isLong ? "bg-[#26a69a]/5" : "bg-[#ef5350]/5";
  const badgeLabel = data.confidence <= 3 ? "HOLD" : isLong ? "LONG" : "BEARISH";
  const badgeClass = data.confidence <= 3
    ? "text-muted-foreground bg-muted text-xs"
    : isLong
      ? "text-[#26a69a] bg-[#26a69a]/10 text-xs"
      : "text-[#ef5350] bg-[#ef5350]/10 text-xs";

  const plan = data.trading_plan;

  // If no trading plan available, show fallback
  if (!plan) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold">
              Kế Hoạch Giao Dịch
            </CardTitle>
            <Badge className={badgeClass}>{badgeLabel}</Badge>
          </div>
        </CardHeader>
        <CardContent className={cn("border-l-4", borderColor, bgTint)}>
          <div className="mb-4">
            <p className="text-xs text-muted-foreground mb-1">Độ tin cậy</p>
            <ScoreBar score={data.confidence} />
          </div>
          <p className="text-sm text-muted-foreground text-center py-4 opacity-60">
            Chưa có kế hoạch giao dịch cụ thể
          </p>
          {data.reasoning && (
            <p className="text-xs text-muted-foreground mt-3 leading-relaxed border-t pt-3">
              {data.reasoning}
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">
            Kế Hoạch Giao Dịch
          </CardTitle>
          <Badge variant="secondary" className={badgeClass}>
            {badgeLabel}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className={cn("rounded-lg p-4 border-l-2", data.confidence <= 3 ? "border-muted" : borderColor, data.confidence <= 3 ? "bg-muted/30" : bgTint)}>
          {/* Confidence */}
          <div className="mb-4">
            <p className="text-xs text-muted-foreground mb-1">Độ tin cậy</p>
            <ScoreBar score={data.confidence} />
          </div>

          {data.confidence <= 3 ? (
            <p className="text-sm text-muted-foreground text-center py-4 opacity-60">
              {data.confidence === 0 ? "Tín hiệu không hợp lệ" : "Nên HOLD — tín hiệu chưa đủ mạnh"}
            </p>
          ) : (
            <>
              {/* Price levels */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-xs text-muted-foreground">Giá vào</span>
                  <p className="font-mono text-sm font-semibold">{fmt(plan.entry_price)}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Cắt lỗ</span>
                  <p className="font-mono text-sm font-semibold text-[#ef5350]">{fmt(plan.stop_loss)}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Chốt lời 1</span>
                  <p className="font-mono text-sm font-semibold text-[#26a69a]">{fmt(plan.take_profit_1)}</p>
                </div>
                {Math.abs(plan.take_profit_2 - plan.take_profit_1) > 1 && (
                  <div>
                    <span className="text-xs text-muted-foreground">Chốt lời 2</span>
                    <p className="font-mono text-sm font-semibold text-[#26a69a]">{fmt(plan.take_profit_2)}</p>
                  </div>
                )}
              </div>

              {/* Meta info */}
              <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-border">
                <div>
                  <span className="text-xs text-muted-foreground">R:R</span>
                  <p className="font-mono text-sm font-semibold">1:{plan.risk_reward_ratio.toFixed(1)}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Khối lượng</span>
                  <p className="font-mono text-sm font-semibold">{Math.round(plan.position_size_pct)}%</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Timeframe</span>
                  <p className="font-mono text-sm font-semibold">
                    {TIMEFRAME_LABELS[plan.timeframe] ?? plan.timeframe}
                  </p>
                </div>
              </div>

              {/* Reasoning */}
              {data.reasoning && (
                <div className="mt-4 pt-3 border-t border-border">
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {data.reasoning}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/** Empty state — exported for use when no trading signal data exists. */
export function TradingPlanEmpty() {
  return (
    <Card>
      <CardContent className="py-8 text-center">
        <p className="text-sm text-muted-foreground">
          Chưa có kế hoạch giao dịch
        </p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          Dữ liệu sẽ có sau khi phân tích AI chạy xong.
        </p>
      </CardContent>
    </Card>
  );
}
