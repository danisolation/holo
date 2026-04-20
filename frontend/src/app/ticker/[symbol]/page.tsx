"use client";

import { use, useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Star,
  StarOff,
  BarChart3,
  RefreshCw,
  Sparkles,
  Check,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ExchangeBadge } from "@/components/exchange-badge";
import { CandlestickChart } from "@/components/candlestick-chart";
import { IndicatorChart } from "@/components/indicator-chart";
import { SupportResistanceCard } from "@/components/support-resistance-card";
import {
  AnalysisCard,
  CombinedRecommendationCard,
} from "@/components/analysis-card";
import { TradingPlanPanel } from "@/components/trading-plan-panel";
import { PTSignalOutcomes } from "@/components/paper-trading/pt-signal-outcomes";
import {
  usePrices,
  useIndicators,
  useAnalysisSummary,
  useTradingSignal,
  useTickers,
  useTriggerAnalysis,
} from "@/lib/hooks";
import { useWatchlistStore } from "@/lib/store";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import { PriceFlashCell } from "@/components/price-flash-cell";

/** AnalyzeNow button — shows for non-watchlisted HNX/UPCOM tickers without recent analysis */
function AnalyzeNowButton({ symbol, exchange, isWatchlisted, hasRecentAnalysis }: {
  symbol: string;
  exchange: string;
  isWatchlisted: boolean;
  hasRecentAnalysis: boolean;
}) {
  const { mutate, isPending, isSuccess, isError } = useTriggerAnalysis();
  const [cooldown, setCooldown] = useState(0);

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  // Start cooldown after trigger (success or error)
  useEffect(() => {
    if (isSuccess || isError) {
      setCooldown(60);
    }
  }, [isSuccess, isError]);

  // Only show for HNX/UPCOM, non-watchlisted, no recent analysis
  if (exchange === "HOSE") return null;
  if (isWatchlisted) return null;
  if (hasRecentAnalysis) return null;

  const isDisabled = isPending || cooldown > 0;

  return (
    <div className="flex items-center gap-3">
      <Button
        variant={isSuccess ? "outline" : "default"}
        size="sm"
        disabled={isDisabled}
        onClick={() => mutate(symbol)}
        aria-busy={isPending}
        className="gap-1.5"
      >
        {isPending ? (
          <>
            <Loader2 className="size-3.5 animate-spin" />
            Đang phân tích...
          </>
        ) : isSuccess ? (
          <>
            <Check className="size-3.5" />
            Đã phân tích
          </>
        ) : cooldown > 0 ? (
          `Thử lại sau ${cooldown}s`
        ) : (
          <>
            <Sparkles className="size-3.5" />
            Phân tích ngay
          </>
        )}
      </Button>
      {isError && (
        <p className="text-sm text-destructive">
          Không thể phân tích. Thử lại sau.
        </p>
      )}
    </div>
  );
}

export default function TickerDetailPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = use(params);
  const upperSymbol = symbol.toUpperCase();
  const router = useRouter();
  const [adjusted, setAdjusted] = useState(true);

  // Data hooks
  const { data: tickers } = useTickers();
  const {
    data: priceData,
    isLoading: pricesLoading,
    error: pricesError,
    refetch: refetchPrices,
  } = usePrices(upperSymbol, 730, adjusted);
  const {
    data: indicatorData,
    isLoading: indicatorsLoading,
  } = useIndicators(upperSymbol, 365);
  const {
    data: analysisSummary,
    isLoading: analysisLoading,
  } = useAnalysisSummary(upperSymbol);
  const { data: tradingSignal, isLoading: tradingSignalLoading } = useTradingSignal(upperSymbol);

  // Derive recommended direction's trading plan for chart overlay
  const tradingPlanForChart = useMemo(() => {
    if (!tradingSignal) return undefined;
    const analysis = tradingSignal.recommended_direction === "long"
      ? tradingSignal.long_analysis
      : tradingSignal.bearish_analysis;
    if (analysis.confidence === 0) return undefined;
    return {
      entry_price: analysis.trading_plan.entry_price,
      stop_loss: analysis.trading_plan.stop_loss,
      take_profit_1: analysis.trading_plan.take_profit_1,
      take_profit_2: analysis.trading_plan.take_profit_2,
    };
  }, [tradingSignal]);

  // Watchlist
  const { addToWatchlist, removeFromWatchlist, isInWatchlist } =
    useWatchlistStore();
  const inWatchlist = isInWatchlist(upperSymbol);

  // Ticker metadata
  const ticker = tickers?.find((t) => t.symbol === upperSymbol);

  // Check if recent analysis exists
  const hasRecentAnalysis = !!analysisSummary?.combined;

  // Real-time price
  const { prices: realtimePrices } = useRealtimePrices([upperSymbol]);
  const rtPrice = realtimePrices[upperSymbol];

  return (
    <div className="space-y-6">
      {/* Ticker header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/")}
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 text-primary" />
          <h1 className="text-lg font-semibold tracking-tight font-mono">
            {upperSymbol}
          </h1>
          {ticker?.exchange && (
            <ExchangeBadge exchange={ticker.exchange} />
          )}
          {ticker && (
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {ticker.name}
            </span>
          )}
          {/* Live price display */}
          {rtPrice && (
            <PriceFlashCell value={rtPrice.price}>
              <span className="font-mono text-sm font-semibold">
                {rtPrice.price.toLocaleString("vi-VN")}
              </span>
              <span
                className={`font-mono text-xs ml-1 ${
                  rtPrice.change_pct > 0
                    ? "text-[#26a69a]"
                    : rtPrice.change_pct < 0
                      ? "text-[#ef5350]"
                      : "text-muted-foreground"
                }`}
              >
                {rtPrice.change_pct >= 0 ? "+" : ""}
                {rtPrice.change_pct.toFixed(2)}%
              </span>
            </PriceFlashCell>
          )}
        </div>
        <div className="ml-auto">
          <Button
            variant={inWatchlist ? "default" : "outline"}
            size="sm"
            onClick={() =>
              inWatchlist
                ? removeFromWatchlist(upperSymbol)
                : addToWatchlist(upperSymbol)
            }
            className="gap-1.5"
          >
            {inWatchlist ? (
              <>
                <Star className="size-3.5 fill-current" />
                Đang theo dõi
              </>
            ) : (
              <>
                <StarOff className="size-3.5" />
                Theo dõi
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Candlestick Chart */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Biểu đồ giá</h2>
          {pricesError && (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => refetchPrices()}
              className="gap-1 text-destructive"
            >
              <RefreshCw className="size-3" />
              Thử lại
            </Button>
          )}
        </div>
        {pricesLoading ? (
          <Skeleton className="h-[420px] rounded-xl" />
        ) : pricesError ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-destructive font-medium mb-2">
                Không thể tải dữ liệu giá
              </p>
              <p className="text-sm text-muted-foreground">
                {pricesError instanceof Error
                  ? pricesError.message
                  : "Lỗi không xác định"}
              </p>
            </CardContent>
          </Card>
        ) : priceData ? (
          <CandlestickChart
            priceData={priceData}
            indicatorData={indicatorData ?? undefined}
            adjusted={adjusted}
            onAdjustedChange={setAdjusted}
            tradingPlan={tradingPlanForChart}
          />
        ) : null}
      </section>

      {/* Indicator Charts */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Chỉ báo kỹ thuật</h2>
        {indicatorsLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-[160px] rounded-lg" />
            <Skeleton className="h-[160px] rounded-lg" />
          </div>
        ) : indicatorData ? (
          <IndicatorChart indicatorData={indicatorData} />
        ) : (
          <div className="text-sm text-muted-foreground">
            Không có dữ liệu chỉ báo
          </div>
        )}
      </section>

      {/* Support & Resistance Levels */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Hỗ trợ & Kháng cự</h2>
        {indicatorsLoading ? (
          <Skeleton className="h-[220px] rounded-xl" />
        ) : indicatorData ? (
          <SupportResistanceCard indicatorData={indicatorData} />
        ) : (
          <div className="text-sm text-muted-foreground">
            Không có dữ liệu hỗ trợ & kháng cự
          </div>
        )}
      </section>

      <Separator />

      {/* Combined Recommendation */}
      {analysisLoading ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : analysisSummary?.combined ? (
        <section>
          <CombinedRecommendationCard analysis={analysisSummary.combined} />
        </section>
      ) : null}

      {/* Trading Plan Panel — Phase 20 */}
      {tradingSignalLoading ? (
        <Skeleton className="h-[320px] rounded-xl" />
      ) : tradingSignal ? (
        <section>
          <TradingPlanPanel data={tradingSignal} symbol={upperSymbol} />
        </section>
      ) : null}

      {/* Signal Outcome History — Phase 25 (UI-05) */}
      <section>
        <PTSignalOutcomes symbol={upperSymbol} />
      </section>

      {/* Analysis Cards Grid */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">
            Phân tích AI đa chiều
          </h2>
          <AnalyzeNowButton
            symbol={upperSymbol}
            exchange={ticker?.exchange ?? "HOSE"}
            isWatchlisted={inWatchlist}
            hasRecentAnalysis={hasRecentAnalysis}
          />
        </div>
        {analysisLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-48 rounded-xl" />
            ))}
          </div>
        ) : analysisSummary ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {analysisSummary.technical && (
              <AnalysisCard
                analysis={analysisSummary.technical}
                type="technical"
              />
            )}
            {analysisSummary.fundamental && (
              <AnalysisCard
                analysis={analysisSummary.fundamental}
                type="fundamental"
              />
            )}
            {analysisSummary.sentiment && (
              <AnalysisCard
                analysis={analysisSummary.sentiment}
                type="sentiment"
              />
            )}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground text-sm">
              Chưa có phân tích AI. Nhấn &ldquo;Phân tích ngay&rdquo; để bắt đầu.
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
