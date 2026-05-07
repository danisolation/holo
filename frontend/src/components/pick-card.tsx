"use client";

import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreBar } from "@/components/analysis-card";
import { formatVND, formatPrice } from "@/lib/format";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import { postBehaviorEvent } from "@/lib/api";
import type { DailyPickResponse } from "@/lib/api";

interface PickCardProps {
  pick: DailyPickResponse;
  onRecordTrade?: (pick: DailyPickResponse) => void;
}

export function PickCard({ pick, onRecordTrade }: PickCardProps) {
  const { prices } = useRealtimePrices([pick.ticker_symbol]);
  const realtimeData = prices[pick.ticker_symbol.toUpperCase()];
  const currentPrice = realtimeData?.price ?? null;

  // P&L calculation
  let pnlPct: number | null = null;
  if (currentPrice != null && pick.entry_price != null && pick.entry_price > 0) {
    pnlPct = ((currentPrice - pick.entry_price) / pick.entry_price) * 100;
  }

  return (
    <Card
      aria-label={`${pick.ticker_symbol} — gợi ý #${pick.rank}`}
      className="cursor-pointer"
      onClick={() => postBehaviorEvent({ event_type: "pick_click", ticker_symbol: pick.ticker_symbol }).catch(() => {})}
    >
      <CardHeader>
        {/* Row 1: Rank + Symbol + Name + Score */}
        <div className="flex items-center gap-2">
          <Badge
            variant="secondary"
            className="text-[#26a69a] bg-[#26a69a]/10"
          >
            #{pick.rank}
          </Badge>
          <span className="font-mono text-sm font-bold">
            {pick.ticker_symbol}
          </span>
          <span className="text-sm text-muted-foreground truncate flex-1">
            {pick.ticker_name}
          </span>
          <div className="w-24 shrink-0">
            <ScoreBar score={pick.composite_score} />
          </div>
        </div>

        {/* Row 2: Direction + Timeframe badges */}
        <div className="flex items-center gap-2 mt-1">
          <Badge className="text-[#26a69a] bg-[#26a69a]/10">MUA</Badge>
          <Badge variant="outline">Swing 3-15 ngày</Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* Section 1: Vietnamese explanation */}
        <div>
          {pick.explanation ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              {pick.explanation}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              Giải thích đang được tạo...
            </p>
          )}
        </div>

        {/* Section 2: Price levels */}
        <div className="border-t border-border pt-4 mt-4">
          <div className="grid grid-cols-2 gap-y-2">
            <span className="text-xs text-muted-foreground">Giá vào</span>
            <span className="font-mono text-sm font-bold text-right">
              {pick.entry_price != null ? formatPrice(pick.entry_price) : "—"}
            </span>

            <span className="text-xs text-muted-foreground">Cắt lỗ</span>
            <span className="font-mono text-sm font-bold text-right text-[#ef5350]">
              {pick.stop_loss != null ? formatPrice(pick.stop_loss) : "—"}
            </span>

            <span className="text-xs text-muted-foreground">Chốt lời 1</span>
            <span className="font-mono text-sm font-bold text-right text-[#26a69a]">
              {pick.take_profit_1 != null
                ? formatPrice(pick.take_profit_1)
                : "—"}
            </span>

            {pick.take_profit_2 != null && (
              <>
                <span className="text-xs text-muted-foreground">
                  Chốt lời 2
                </span>
                <span className="font-mono text-sm font-bold text-right text-[#26a69a]">
                  {formatPrice(pick.take_profit_2)}
                </span>
              </>
            )}

            <span className="text-xs text-muted-foreground">Tỷ lệ R:R</span>
            <span className="font-mono text-sm font-bold text-right">
              {pick.risk_reward != null
                ? `1:${pick.risk_reward.toFixed(1)}`
                : "—"}
            </span>
          </div>
        </div>

        {/* Section 3: Position sizing */}
        {pick.position_size_shares != null &&
          pick.entry_price != null &&
          pick.position_size_vnd != null && (
            <div className="border-t border-border pt-4 mt-4">
              <div className="bg-muted rounded-lg p-4 text-sm">
                Mua {pick.position_size_shares} cổ ×{" "}
                {formatPrice(pick.entry_price)}đ ={" "}
                {formatVND(pick.position_size_vnd)} VND (
                {pick.position_size_pct?.toFixed(1)}% vốn)
              </div>
            </div>
          )}

        {/* Section 4: Live price */}
        <div className="border-t border-border pt-4 mt-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Giá hiện tại
            </span>
            <div className="flex items-center gap-2" aria-live="polite">
              {currentPrice != null ? (
                <>
                  <span className="font-mono text-sm font-bold">
                    {formatPrice(currentPrice)}
                  </span>
                  {pnlPct != null && pnlPct > 0 && (
                    <Badge className="text-[#26a69a] bg-[#26a69a]/10">
                      ▲ +{pnlPct.toFixed(1)}%
                    </Badge>
                  )}
                  {pnlPct != null && pnlPct < 0 && (
                    <Badge className="text-[#ef5350] bg-[#ef5350]/10">
                      ▼ {pnlPct.toFixed(1)}%
                    </Badge>
                  )}
                  {pnlPct != null && pnlPct === 0 && (
                    <Badge variant="outline">— 0.0%</Badge>
                  )}
                </>
              ) : (
                <span className="font-mono text-sm text-muted-foreground">
                  —
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Section 5: Record trade button */}
        {onRecordTrade && (
          <div className="border-t border-border pt-4 mt-4">
            <Button
              className="w-full"
              onClick={(e) => {
                e.stopPropagation();
                onRecordTrade(pick);
              }}
            >
              Ghi nhận giao dịch
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PickCardSkeleton() {
  return <Skeleton className="h-[400px] rounded-xl" />;
}
