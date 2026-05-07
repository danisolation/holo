"use client";

import { use, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Star,
  StarOff,
  BarChart3,
  RefreshCw,
  Brain,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import dynamic from "next/dynamic";

const CandlestickChart = dynamic(
  () =>
    import("@/components/candlestick-chart").then((m) => ({
      default: m.CandlestickChart,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[400px] rounded-xl" /> },
);
const IndicatorChart = dynamic(
  () =>
    import("@/components/indicator-chart").then((m) => ({
      default: m.IndicatorChart,
    })),
  { ssr: false, loading: () => <Skeleton className="h-[200px] rounded-xl" /> },
);

import { SupportResistanceCard } from "@/components/support-resistance-card";
import {
  AnalysisCard,
  StructuredCombinedCard,
} from "@/components/analysis-card";
import { TradingPlanPanel } from "@/components/trading-plan-panel";
import { RumorScorePanel } from "@/components/rumor-score-panel";
import {
  usePrices,
  useIndicators,
  useAnalysisSummary,
  useTradingSignal,
  useTickerNews,
  useRumorScores,
  useTickers,
  useWatchlist,
  useAddToWatchlist,
  useRemoveFromWatchlist,
} from "@/lib/hooks";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import { useBehaviorTracking } from "@/lib/use-behavior-tracking";
import { PriceFlashCell } from "@/components/price-flash-cell";
import { BidAskPanel } from "@/components/bid-ask-panel";
import { NewsList } from "@/components/news-list";
import { NewsListSkeleton } from "@/components/news-list-skeleton";

/** Inline error card for individual sections */
function SectionError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between py-4">
        <p className="text-sm text-destructive">
          {error.message || "Lỗi không xác định"}
        </p>
        <Button variant="ghost" size="xs" onClick={onRetry} className="gap-1 text-destructive">
          <RefreshCw className="size-3" />
          Thử lại
        </Button>
      </CardContent>
    </Card>
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

  // Data hooks
  const { data: tickers } = useTickers();
  useBehaviorTracking("ticker_view", upperSymbol);
  const {
    data: priceData,
    isLoading: pricesLoading,
    error: pricesError,
    refetch: refetchPrices,
  } = usePrices(upperSymbol, 730);
  const {
    data: indicatorData,
    isLoading: indicatorsLoading,
    error: indicatorsError,
    refetch: refetchIndicators,
  } = useIndicators(upperSymbol, 365);
  const {
    data: analysisSummary,
    isLoading: analysisLoading,
    error: analysisError,
    refetch: refetchAnalysis,
  } = useAnalysisSummary(upperSymbol);
  const {
    data: tradingSignal,
    isLoading: tradingSignalLoading,
    error: tradingSignalError,
    refetch: refetchTradingSignal,
  } = useTradingSignal(upperSymbol);
  const {
    data: newsArticles,
    isLoading: newsLoading,
    error: newsError,
    refetch: refetchNews,
  } = useTickerNews(upperSymbol);
  const {
    data: rumorData,
    isLoading: rumorsLoading,
    error: rumorsError,
    refetch: refetchRumors,
  } = useRumorScores(upperSymbol);

  // Derive trading plan for chart overlay
  const tradingPlanForChart = useMemo(() => {
    if (!tradingSignal || tradingSignal.confidence === 0) return undefined;
    if (!tradingSignal.trading_plan) return undefined;
    return {
      entry_price: tradingSignal.trading_plan.entry_price,
      stop_loss: tradingSignal.trading_plan.stop_loss,
      take_profit_1: tradingSignal.trading_plan.take_profit_1,
      take_profit_2: tradingSignal.trading_plan.take_profit_2,
    };
  }, [tradingSignal]);

  // Watchlist
  const { data: watchlistData } = useWatchlist();
  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();
  const inWatchlist = watchlistData?.some((w) => w.symbol === upperSymbol) ?? false;

  // Ticker metadata
  const ticker = tickers?.find((t) => t.symbol === upperSymbol);

  // On-demand AI analysis
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeProgress, setAnalyzeProgress] = useState("");
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const handleAnalyzeNow = async () => {
    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalyzeProgress("Đang khởi tạo phân tích...");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/analysis/${upperSymbol}/analyze-now`,
        { method: "POST" }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      // Poll every 5s until analysis appears (max 90s)
      const steps = [
        "Phân tích kỹ thuật...",
        "Phân tích sentiment...",
        "Tổng hợp đa chiều...",
        "Tạo kế hoạch giao dịch...",
        "Hoàn tất...",
      ];
      let attempt = 0;
      const maxAttempts = 18; // 18 * 5s = 90s
      const poll = setInterval(async () => {
        attempt++;
        setAnalyzeProgress(steps[Math.min(Math.floor(attempt / 4), steps.length - 1)]);
        try {
          const check = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/analysis/${upperSymbol}/summary`
          );
          if (check.ok) {
            const data = await check.json();
            // Check if combined analysis is fresh (updated in last 2 min)
            if (data?.combined?.analysis_date === new Date().toISOString().slice(0, 10)) {
              clearInterval(poll);
              refetchAnalysis();
              refetchTradingSignal();
              setAnalyzing(false);
              setAnalyzeProgress("");
              return;
            }
          }
        } catch { /* ignore poll errors */ }
        if (attempt >= maxAttempts) {
          clearInterval(poll);
          refetchAnalysis();
          refetchTradingSignal();
          setAnalyzing(false);
          setAnalyzeProgress("");
        }
      }, 5000);
    } catch (e) {
      setAnalyzeError(e instanceof Error ? e.message : "Lỗi không xác định");
      setAnalyzing(false);
      setAnalyzeProgress("");
    }
  };

  // Real-time price
  const { prices: realtimePrices } = useRealtimePrices([upperSymbol]);
  const rtPrice = realtimePrices[upperSymbol];

  return (
    <div data-testid="ticker-page" className="space-y-6">
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
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={handleAnalyzeNow}
            disabled={analyzing}
            className="gap-1.5"
          >
            {analyzing ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                {analyzeProgress || "Đang phân tích..."}
              </>
            ) : (
              <>
                <Brain className="size-3.5" />
                Phân tích AI
              </>
            )}
          </Button>
          <Button
            variant={inWatchlist ? "default" : "outline"}
            size="sm"
            onClick={() =>
              inWatchlist
                ? removeMutation.mutate(upperSymbol)
                : addMutation.mutate(upperSymbol)
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

      {/* Analyze error message */}
      {analyzeError && (
        <Card>
          <CardContent className="py-3">
            <p className="text-sm text-destructive">{analyzeError}</p>
          </CardContent>
        </Card>
      )}

      {/* Candlestick Chart */}
      <section data-testid="ticker-chart">
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
            tradingPlan={tradingPlanForChart}
            realtimePrice={rtPrice ? { price: rtPrice.price, high: rtPrice.high, low: rtPrice.low, open: rtPrice.open } : null}
          />
        ) : null}
      </section>

      {/* Bid/Ask Depth Panel (FE-03) */}
      {rtPrice?.bid_ask && (
        <section data-testid="bid-ask-panel">
          <h2 className="text-lg font-semibold mb-3">Sổ lệnh (Bid/Ask)</h2>
          <Card>
            <CardContent className="py-4">
              <BidAskPanel data={rtPrice.bid_ask} refPrice={rtPrice.ref_price} />
            </CardContent>
          </Card>
        </section>
      )}

      {/* Indicator Charts */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Chỉ báo kỹ thuật</h2>
        {indicatorsLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-[160px] rounded-lg" />
            <Skeleton className="h-[160px] rounded-lg" />
          </div>
        ) : indicatorsError ? (
          <SectionError error={indicatorsError} onRetry={() => refetchIndicators()} />
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
        ) : indicatorsError ? (
          <SectionError error={indicatorsError} onRetry={() => refetchIndicators()} />
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
      {analysisLoading || analyzing ? (
        <Skeleton className="h-32 rounded-xl" />
      ) : analysisError ? (
        <SectionError error={analysisError} onRetry={() => refetchAnalysis()} />
      ) : analysisSummary?.combined ? (
        <section>
          <StructuredCombinedCard analysis={analysisSummary.combined} />
        </section>
      ) : null}

      {/* Trading Plan Panel — Phase 20 */}
      {tradingSignalLoading || analyzing ? (
        <Skeleton className="h-[320px] rounded-xl" />
      ) : tradingSignalError ? (
        <SectionError error={tradingSignalError} onRetry={() => refetchTradingSignal()} />
      ) : tradingSignal ? (
        <section>
          <TradingPlanPanel data={tradingSignal} symbol={upperSymbol} />
        </section>
      ) : null}

      {/* Analysis Cards Grid */}
      <section>
        <h2 className="text-lg font-semibold mb-3">
          Phân tích AI đa chiều
        </h2>
        {analysisLoading || analyzing ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-48 rounded-xl" />
            ))}
          </div>
        ) : analysisError ? (
          <SectionError error={analysisError} onRetry={() => refetchAnalysis()} />
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

      {/* Recent News from CafeF */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Tin tức CafeF</h2>
        {newsLoading ? (
          <NewsListSkeleton />
        ) : newsError ? (
          <SectionError error={newsError} onRetry={() => refetchNews()} />
        ) : newsArticles && newsArticles.length > 0 ? (
          <NewsList articles={newsArticles} />
        ) : null}
      </section>

      {/* Rumor Intelligence — Phase 62 */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Tin đồn cộng đồng</h2>
        {rumorsLoading ? (
          <Skeleton className="h-32 rounded-xl" />
        ) : rumorsError ? (
          <SectionError error={rumorsError} onRetry={() => refetchRumors()} />
        ) : rumorData ? (
          <div className="space-y-4">
            <RumorScorePanel data={rumorData} />
          </div>
        ) : null}
      </section>
    </div>
  );
}
