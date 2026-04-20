"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreBar } from "@/components/analysis-card";
import { cn } from "@/lib/utils";
import { useCreateManualFollow } from "@/lib/hooks";
import { Check, Loader2 } from "lucide-react";
import type { TickerTradingSignal, DirectionAnalysis } from "@/lib/api";

const fmt = (v: number) => Math.round(v).toLocaleString("vi-VN");

const TIMEFRAME_LABELS: Record<string, string> = {
  swing: "Swing (3-15 ngày)",
  position: "Position (vài tuần+)",
};

/** Internal sub-component — renders a single direction column (LONG or BEARISH). */
function DirectionColumn({
  analysis,
  isRecommended,
  symbol,
}: {
  analysis: DirectionAnalysis;
  isRecommended: boolean;
  symbol: string;
}) {
  const isLong = analysis.direction === "long";
  const followMutation = useCreateManualFollow();

  const borderColor = isLong ? "border-[#26a69a]" : "border-[#ef5350]";
  const bgTint = isLong ? "bg-[#26a69a]/5" : "bg-[#ef5350]/5";
  const badgeClass = isLong
    ? "text-[#26a69a] bg-[#26a69a]/10 text-[10px]"
    : "text-[#ef5350] bg-[#ef5350]/10 text-[10px]";

  const plan = analysis.trading_plan;

  return (
    <div
      className={cn(
        "rounded-lg p-3",
        isRecommended && "border-l-2",
        isRecommended && borderColor,
        isRecommended && bgTint,
      )}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 mb-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {isLong ? "LONG" : "XU HƯỚNG GIẢM"}
        </p>
        {isRecommended && (
          <Badge variant="secondary" className={badgeClass}>
            Khuyến nghị
          </Badge>
        )}
      </div>

      {/* Confidence */}
      <div className="mb-3">
        <p className="text-xs text-muted-foreground mb-1">Độ tin cậy</p>
        <ScoreBar score={analysis.confidence} />
      </div>

      {/* Invalid signal check */}
      {analysis.confidence === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-4 opacity-60">
          Tín hiệu không hợp lệ
        </p>
      ) : (
        <>
          {/* Price rows */}
          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Giá vào
            </span>
            <span className="font-mono text-sm font-semibold">
              {fmt(plan.entry_price)}
            </span>
          </div>

          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Cắt lỗ
            </span>
            <span className="font-mono text-sm font-semibold text-[#ef5350]">
              {fmt(plan.stop_loss)}
            </span>
          </div>

          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Chốt lời 1
            </span>
            <span className="font-mono text-sm font-semibold text-[#26a69a]">
              {fmt(plan.take_profit_1)}
            </span>
          </div>

          {Math.abs(plan.take_profit_2 - plan.take_profit_1) > 1 && (
            <div className="flex items-center justify-between py-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                Chốt lời 2
              </span>
              <span className="font-mono text-sm font-semibold text-[#26a69a]">
                {fmt(plan.take_profit_2)}
              </span>
            </div>
          )}

          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Tỷ lệ R:R
            </span>
            <span className="font-mono text-sm font-semibold">
              1:{plan.risk_reward_ratio.toFixed(1)}
            </span>
          </div>

          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Khối lượng
            </span>
            <span className="font-mono text-sm font-semibold">
              {Math.round(plan.position_size_pct)}%
            </span>
          </div>

          <div className="flex items-center justify-between py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Khung thời gian
            </span>
            <span className="font-mono text-sm font-semibold">
              {TIMEFRAME_LABELS[plan.timeframe] ?? plan.timeframe}
            </span>
          </div>

          {/* Reasoning */}
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs leading-relaxed text-muted-foreground">
              {analysis.reasoning}
            </p>
          </div>

          {/* PT-09: Follow button */}
          <div className="mt-3">
            <Button
              size="sm"
              variant={followMutation.isSuccess ? "outline" : "default"}
              className="w-full"
              disabled={followMutation.isPending || followMutation.isSuccess}
              onClick={() =>
                followMutation.mutate({
                  symbol,
                  direction: analysis.direction,
                  entry_price: plan.entry_price,
                  stop_loss: plan.stop_loss,
                  take_profit_1: plan.take_profit_1,
                  take_profit_2: plan.take_profit_2,
                  timeframe: plan.timeframe,
                  confidence: analysis.confidence,
                  position_size_pct: plan.position_size_pct,
                })
              }
            >
              {followMutation.isPending ? (
                <Loader2 className="size-4 animate-spin mr-1" />
              ) : followMutation.isSuccess ? (
                <Check className="size-4 mr-1" />
              ) : null}
              {followMutation.isSuccess ? "Đã follow" : "Follow"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

/** Two-column LONG / BEARISH trading plan panel. */
interface TradingPlanPanelProps {
  data: TickerTradingSignal;
  symbol: string;
}

export function TradingPlanPanel({ data, symbol }: TradingPlanPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">
          Kế Hoạch Giao Dịch
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <DirectionColumn
            analysis={data.long_analysis}
            isRecommended={data.recommended_direction === "long"}
            symbol={symbol}
          />
          <DirectionColumn
            analysis={data.bearish_analysis}
            isRecommended={data.recommended_direction === "bearish"}
            symbol={symbol}
          />
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
