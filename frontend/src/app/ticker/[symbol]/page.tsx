"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Star,
  StarOff,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { CandlestickChart } from "@/components/candlestick-chart";
import { IndicatorChart } from "@/components/indicator-chart";
import {
  AnalysisCard,
  CombinedRecommendationCard,
} from "@/components/analysis-card";
import {
  usePrices,
  useIndicators,
  useAnalysisSummary,
  useTickers,
} from "@/lib/hooks";
import { useWatchlistStore } from "@/lib/store";

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
  const {
    data: priceData,
    isLoading: pricesLoading,
    error: pricesError,
    refetch: refetchPrices,
  } = usePrices(upperSymbol, 730);
  const {
    data: indicatorData,
    isLoading: indicatorsLoading,
  } = useIndicators(upperSymbol, 365);
  const {
    data: analysisSummary,
    isLoading: analysisLoading,
  } = useAnalysisSummary(upperSymbol);

  // Watchlist
  const { addToWatchlist, removeFromWatchlist, isInWatchlist } =
    useWatchlistStore();
  const inWatchlist = isInWatchlist(upperSymbol);

  // Ticker metadata
  const ticker = tickers?.find((t) => t.symbol === upperSymbol);

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center gap-4 px-4 mx-auto max-w-7xl">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => router.push("/")}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div className="flex items-center gap-2">
            <BarChart3 className="size-5 text-primary" />
            <h1 className="text-lg font-bold tracking-tight font-mono">
              {upperSymbol}
            </h1>
            {ticker && (
              <span className="text-sm text-muted-foreground hidden sm:inline">
                {ticker.name}
              </span>
            )}
          </div>
          <div className="ml-auto flex items-center gap-2">
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
      </header>

      {/* Main */}
      <main className="flex-1 container px-4 py-6 mx-auto max-w-7xl space-y-6">
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

        <Separator />

        {/* Combined Recommendation */}
        {analysisLoading ? (
          <Skeleton className="h-32 rounded-xl" />
        ) : analysisSummary?.combined ? (
          <section>
            <CombinedRecommendationCard analysis={analysisSummary.combined} />
          </section>
        ) : null}

        {/* Analysis Cards Grid */}
        <section>
          <h2 className="text-lg font-semibold mb-3">
            Phân tích AI đa chiều
          </h2>
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
                Chưa có dữ liệu phân tích AI cho mã {upperSymbol}
              </CardContent>
            </Card>
          )}
        </section>
      </main>
    </div>
  );
}
