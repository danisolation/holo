"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchTickers,
  fetchPrices,
  fetchIndicators,
  fetchAnalysisSummary,
  fetchTradingSignal,
  fetchUnifiedAnalysis,
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
  fetchWatchlist,
  addWatchlistItem,
  removeWatchlistItem,
  updateWatchlistSector,
  fetchSectors,
  fetchDiscovery,
  fetchRumorScores,
  fetchWatchlistRumors,
  fetchAccuracyStats,
  fetchTickerAccuracy,
  fetchSimulatorPortfolio,
  createSimulatorTrade,
  fetchSimulatorTrades,
  fetchSimulatorStats,
  resetSimulatorPortfolio,
  fetchPendingSignals,
  executeSignals,
  skipSignals,
} from "@/lib/api";
import type { SimulatorTradeCreate } from "@/lib/api";

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

export function useUnifiedAnalysis(symbol: string | undefined) {
  return useQuery({
    queryKey: ["unified-analysis", symbol],
    queryFn: () => fetchUnifiedAnalysis(symbol!),
    enabled: !!symbol,
    staleTime: 60 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

// --- Phase 49: Watchlist Hooks ---

/** Fetch server-backed watchlist with AI signal data. staleTime: 2 min. */
export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: fetchWatchlist,
    staleTime: 2 * 60 * 1000,
  });
}

/** Add a symbol to watchlist, invalidates watchlist query on success. */
export function useAddToWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => addWatchlistItem(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}

/** Remove a symbol from watchlist, invalidates watchlist query on success. */
export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => removeWatchlistItem(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}

// --- Phase 54: Sector Group Hooks ---

/** Fetch distinct ICB sector names for auto-suggest. staleTime: 10 min (rarely changes). */
export function useSectors() {
  return useQuery({
    queryKey: ["sectors"],
    queryFn: fetchSectors,
    staleTime: 10 * 60 * 1000,
  });
}

/** Update sector_group for a watchlist item, invalidates watchlist query on success. */
export function useUpdateSectorGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ symbol, sectorGroup }: { symbol: string; sectorGroup: string | null }) =>
      updateWatchlistSector(symbol, sectorGroup),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });
}

// --- Phase 55: Discovery Hooks ---

/** Fetch discovery results with optional sector/signal filters. staleTime: 5 min. */
export function useDiscovery(params?: { sector?: string; signal_type?: string }) {
  return useQuery({
    queryKey: ["discovery", params?.sector ?? "all", params?.signal_type ?? "all"],
    queryFn: () => fetchDiscovery(params),
    staleTime: 5 * 60 * 1000,
  });
}

// --- Phase 62: Rumor Hooks ---

/**
 * Fetch rumor scores + posts for a single ticker.
 * staleTime: 5 minutes — rumor data refreshes daily (per D-13).
 */
export function useRumorScores(symbol: string | undefined) {
  return useQuery({
    queryKey: ["rumor-scores", symbol],
    queryFn: () => fetchRumorScores(symbol!),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch rumor summary for all watchlist tickers (badge data).
 * staleTime: 5 minutes (per D-13).
 */
export function useWatchlistRumors() {
  return useQuery({
    queryKey: ["watchlist-rumors"],
    queryFn: fetchWatchlistRumors,
    staleTime: 5 * 60 * 1000,
  });
}

// --- Phase 65: Accuracy Hooks ---

export function useAccuracyStats(days: number = 30) {
  return useQuery({
    queryKey: ["accuracy-stats", days],
    queryFn: () => fetchAccuracyStats(days),
    staleTime: 10 * 60 * 1000,
  });
}

export function useTickerAccuracy(tickerId: number | undefined, days: number = 30) {
  return useQuery({
    queryKey: ["ticker-accuracy", tickerId, days],
    queryFn: () => fetchTickerAccuracy(tickerId!, days),
    enabled: !!tickerId,
    staleTime: 10 * 60 * 1000,
  });
}

// --- Phase 95: Simulator Hooks ---

export function useSimulatorPortfolio() {
  return useQuery({
    queryKey: ["simulator", "portfolio"],
    queryFn: fetchSimulatorPortfolio,
    staleTime: 30_000,
  });
}

export function useSimulatorTrades(page = 1, source?: string) {
  return useQuery({
    queryKey: ["simulator", "trades", page, source],
    queryFn: () => fetchSimulatorTrades(page, 20, source),
    staleTime: 30_000,
  });
}

export function useSimulatorStats() {
  return useQuery({
    queryKey: ["simulator", "stats"],
    queryFn: fetchSimulatorStats,
    staleTime: 60_000,
  });
}

export function useCreateSimulatorTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SimulatorTradeCreate) => createSimulatorTrade(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulator"] });
    },
  });
}

export function useResetSimulator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: resetSimulatorPortfolio,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulator"] });
    },
  });
}

// --- Phase 95-04: Auto-trade signal hooks ---

export function usePendingSignals() {
  return useQuery({
    queryKey: ["simulator", "signals", "pending"],
    queryFn: () => fetchPendingSignals(3),
    staleTime: 60_000,
  });
}

export function useExecuteSignals() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pickIds: number[]) => executeSignals(pickIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulator"] });
    },
  });
}

export function useSkipSignals() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pickIds: number[]) => skipSignals(pickIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulator", "signals"] });
    },
  });
}
