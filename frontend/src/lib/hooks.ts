"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchTickers,
  fetchPrices,
  fetchIndicators,
  fetchAnalysisSummary,
  fetchTradingSignal,
  fetchTickerNews,
  fetchMarketOverview,
  triggerOnDemandAnalysis,
  fetchJobStatuses,
  fetchDataFreshness,
  fetchErrorRates,
  fetchDbPool,
  fetchHealthSummary,
  triggerJob,
  fetchGeminiUsage,
  fetchPipelineTimeline,
  fetchDailyPicks,
  fetchProfile,
  updateProfile,
  fetchTrades,
  fetchTradeStats,
  createTrade,
  deleteTrade,
  fetchPickHistory,
  fetchPickPerformance,
  fetchRiskSuggestion,
  respondRiskSuggestion,
  fetchHabitDetections,
  fetchViewingStats,
  fetchSectorPreferences,
  fetchCurrentGoal,
  setGoal,
  fetchWeeklyPrompt,
  respondWeeklyPrompt,
  fetchLatestReview,
} from "@/lib/api";
import type { ProfileUpdate, TradeCreate } from "@/lib/api";

/**
 * Fetch all active tickers, optionally filtered by sector.
 * staleTime: 5 minutes — ticker list rarely changes.
 */
export function useTickers(sector?: string, exchange?: string, limit?: number, offset?: number) {
  return useQuery({
    queryKey: ["tickers", sector ?? "all", exchange ?? "all", limit ?? "default", offset ?? 0],
    queryFn: () => fetchTickers(sector, exchange, limit, offset),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch OHLCV price data for a single ticker.
 * staleTime: 5 minutes — prices update at most once per trading session.
 */
export function usePrices(symbol: string | undefined, days: number = 365) {
  return useQuery({
    queryKey: ["prices", symbol, days],
    queryFn: () => fetchPrices(symbol!, days),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch technical indicator data for a single ticker.
 * staleTime: 5 minutes.
 */
export function useIndicators(symbol: string | undefined, limit: number = 100, offset: number = 0) {
  return useQuery({
    queryKey: ["indicators", symbol, limit, offset],
    queryFn: () => fetchIndicators(symbol!, limit, offset),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch AI analysis summary (technical + fundamental + sentiment + combined).
 * staleTime: 30 minutes — AI analysis is expensive and infrequent.
 */
export function useAnalysisSummary(symbol: string | undefined) {
  return useQuery({
    queryKey: ["analysis-summary", symbol],
    queryFn: () => fetchAnalysisSummary(symbol!),
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

/**
 * Fetch recent news articles for a ticker.
 * staleTime: 10 minutes — news updates infrequently.
 */
export function useTickerNews(symbol: string | undefined, offset: number = 0) {
  return useQuery({
    queryKey: ["ticker-news", symbol, offset],
    queryFn: () => fetchTickerNews(symbol!, 10, offset),
    enabled: !!symbol,
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Fetch market overview: all active tickers with latest price + daily change %.
 * staleTime: 5 minutes.
 */
export function useMarketOverview(exchange?: string, opts?: { sort?: "change_pct" | "market_cap" | "symbol"; order?: "desc" | "asc"; top?: number }) {
  return useQuery({
    queryKey: ["market-overview", exchange ?? "all", opts?.sort ?? "change_pct", opts?.order ?? "desc", opts?.top ?? "all"],
    queryFn: () => fetchMarketOverview({ exchange, ...opts }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTriggerAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => triggerOnDemandAnalysis(symbol),
    onSuccess: (_data, symbol) => {
      // Invalidate analysis summary for the analyzed ticker
      queryClient.invalidateQueries({ queryKey: ["analysis-summary", symbol] });
      // Use a short delay to allow background task to complete
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["analysis-summary", symbol] });
      }, 5000);
    },
  });
}

// --- Health Hooks ---

export function useJobStatuses() {
  return useQuery({
    queryKey: ["health-jobs"],
    queryFn: fetchJobStatuses,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useDataFreshness() {
  return useQuery({
    queryKey: ["health-freshness"],
    queryFn: fetchDataFreshness,
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });
}

export function useErrorRates() {
  return useQuery({
    queryKey: ["health-errors"],
    queryFn: fetchErrorRates,
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });
}

export function useDbPool() {
  return useQuery({
    queryKey: ["health-db-pool"],
    queryFn: fetchDbPool,
    staleTime: 15 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useHealthSummary() {
  return useQuery({
    queryKey: ["health-summary"],
    queryFn: fetchHealthSummary,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useTriggerJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobName: string) => triggerJob(jobName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["health-summary"] });
    },
  });
}

// --- Gemini Usage & Pipeline Timeline Hooks (Phase 15) ---

export function useGeminiUsage(days: number = 7) {
  return useQuery({
    queryKey: ["health-gemini-usage", days],
    queryFn: () => fetchGeminiUsage(days),
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });
}

export function usePipelineTimeline(days: number = 7) {
  return useQuery({
    queryKey: ["health-pipeline-timeline", days],
    queryFn: () => fetchPipelineTimeline(days),
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });
}

// --- Trading Signal Hook (Phase 20) ---

export function useTradingSignal(symbol: string | undefined) {
  return useQuery({
    queryKey: ["trading-signal", symbol],
    queryFn: () => fetchTradingSignal(symbol!),
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

// --- Phase 43: Daily Picks Hooks ---

/**
 * Fetch today's daily picks (3-5 selected + 5-10 almost-selected).
 * staleTime: 5 minutes — picks update once per day after analysis.
 */
export function useDailyPicks() {
  return useQuery({
    queryKey: ["picks", "today"],
    queryFn: () => fetchDailyPicks(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch user risk profile (capital, risk level).
 * staleTime: 10 minutes — rarely changes.
 */
export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => fetchProfile(),
    staleTime: 10 * 60 * 1000,
  });
}

/**
 * Update user risk profile. Invalidates profile + today's picks
 * (picks depend on capital for position sizing).
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProfileUpdate) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["picks", "today"] });
    },
  });
}

// --- Phase 44: Trade Journal Hooks ---

export function useTrades(params?: {
  page?: number;
  ticker?: string;
  side?: string;
  sort?: string;
  order?: string;
}) {
  return useQuery({
    queryKey: ["trades", params?.page ?? 1, params?.ticker ?? "", params?.side ?? "", params?.sort ?? "trade_date", params?.order ?? "desc"],
    queryFn: () => fetchTrades(params),
    staleTime: 30 * 1000,
  });
}

export function useTradeStats() {
  return useQuery({
    queryKey: ["trades", "stats"],
    queryFn: () => fetchTradeStats(),
    staleTime: 30 * 1000,
  });
}

export function useCreateTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TradeCreate) => createTrade(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function useDeleteTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteTrade(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

// --- Phase 45: Pick Performance Hooks ---

export function usePickHistory(params?: { page?: number; status?: string }) {
  return useQuery({
    queryKey: ["picks", "history", params?.page ?? 1, params?.status ?? "all"],
    queryFn: () => fetchPickHistory({ page: params?.page, per_page: 20, status: params?.status }),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePickPerformance() {
  return useQuery({
    queryKey: ["picks", "performance"],
    queryFn: () => fetchPickPerformance(),
    staleTime: 5 * 60 * 1000,
  });
}

// --- Phase 46: Behavior Tracking Hooks ---

export function useRiskSuggestion() {
  return useQuery({
    queryKey: ["behavior", "risk-suggestion"],
    queryFn: fetchRiskSuggestion,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRespondRiskSuggestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: number; action: "accept" | "reject" }) =>
      respondRiskSuggestion(id, { action }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["behavior", "risk-suggestion"] });
      if (variables.action === "accept") {
        queryClient.invalidateQueries({ queryKey: ["profile"] });
        queryClient.invalidateQueries({ queryKey: ["picks", "today"] });
      }
    },
  });
}

export function useHabitDetections() {
  return useQuery({
    queryKey: ["behavior", "habits"],
    queryFn: fetchHabitDetections,
    staleTime: 10 * 60 * 1000,
  });
}

export function useViewingStats() {
  return useQuery({
    queryKey: ["behavior", "viewing-stats"],
    queryFn: fetchViewingStats,
    staleTime: 10 * 60 * 1000,
  });
}

export function useSectorPreferences() {
  return useQuery({
    queryKey: ["behavior", "sector-preferences"],
    queryFn: fetchSectorPreferences,
    staleTime: 10 * 60 * 1000,
  });
}

// --- Phase 47: Goals & Weekly Reviews Hooks ---

export function useCurrentGoal() {
  return useQuery({
    queryKey: ["goals", "current"],
    queryFn: fetchCurrentGoal,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSetGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (target_pnl: number) => setGoal(target_pnl),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals", "current"] });
    },
  });
}

export function useWeeklyPrompt() {
  return useQuery({
    queryKey: ["goals", "weekly-prompt"],
    queryFn: fetchWeeklyPrompt,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRespondWeeklyPrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, response }: { id: number; response: string }) =>
      respondWeeklyPrompt(id, response),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals", "weekly-prompt"] });
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}

export function useLatestReview() {
  return useQuery({
    queryKey: ["goals", "weekly-review"],
    queryFn: fetchLatestReview,
    staleTime: 10 * 60 * 1000,
  });
}
