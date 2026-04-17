"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchTickers,
  fetchPrices,
  fetchIndicators,
  fetchAnalysisSummary,
  fetchMarketOverview,
  triggerOnDemandAnalysis,
  fetchHoldings,
  fetchPortfolioSummary,
  fetchTradeHistory,
  createTrade,
  type TradeRequest,
  fetchPerformanceData,
  fetchAllocationData,
  updateTrade,
  deleteTrade,
  uploadCSVDryRun,
  importCSV,
  type TradeUpdateRequest,
  fetchJobStatuses,
  fetchDataFreshness,
  fetchErrorRates,
  fetchDbPool,
  fetchHealthSummary,
  triggerJob,
  fetchCorporateEvents,
  fetchGeminiUsage,
  fetchPipelineTimeline,
} from "@/lib/api";

/**
 * Fetch all active tickers, optionally filtered by sector.
 * staleTime: 5 minutes — ticker list rarely changes.
 */
export function useTickers(sector?: string, exchange?: string) {
  return useQuery({
    queryKey: ["tickers", sector ?? "all", exchange ?? "all"],
    queryFn: () => fetchTickers(sector, exchange),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch OHLCV price data for a single ticker.
 * staleTime: 5 minutes — prices update at most once per trading session.
 */
export function usePrices(symbol: string | undefined, days: number = 365, adjusted: boolean = true) {
  return useQuery({
    queryKey: ["prices", symbol, days, adjusted],
    queryFn: () => fetchPrices(symbol!, days, adjusted),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Fetch technical indicator data for a single ticker.
 * staleTime: 5 minutes.
 */
export function useIndicators(symbol: string | undefined, limit: number = 100) {
  return useQuery({
    queryKey: ["indicators", symbol, limit],
    queryFn: () => fetchIndicators(symbol!, limit),
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
    staleTime: 30 * 60 * 1000,
  });
}

/**
 * Fetch market overview: all active tickers with latest price + daily change %.
 * staleTime: 5 minutes.
 */
export function useMarketOverview(exchange?: string) {
  return useQuery({
    queryKey: ["market-overview", exchange ?? "all"],
    queryFn: () => fetchMarketOverview(exchange),
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

// --- Portfolio Hooks ---

export function useHoldings() {
  return useQuery({
    queryKey: ["portfolio-holdings"],
    queryFn: fetchHoldings,
    staleTime: 2 * 60 * 1000,
  });
}

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio-summary"],
    queryFn: fetchPortfolioSummary,
    staleTime: 2 * 60 * 1000,
  });
}

export function useTradeHistory(params?: {
  ticker?: string;
  side?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["portfolio-trades", params],
    queryFn: () => fetchTradeHistory(params),
    staleTime: 1 * 60 * 1000,
  });
}

export function useCreateTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (trade: TradeRequest) => createTrade(trade),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio-holdings"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-trades"] });
    },
  });
}

// --- Portfolio Enhancement Hooks (Phase 13) ---

export function usePerformanceData(period: string = "3M") {
  return useQuery({
    queryKey: ["portfolio-performance", period],
    queryFn: () => fetchPerformanceData(period),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAllocationData(mode: "ticker" | "sector" = "ticker") {
  return useQuery({
    queryKey: ["portfolio-allocation", mode],
    queryFn: () => fetchAllocationData(mode),
    staleTime: 2 * 60 * 1000,
  });
}

export function useUpdateTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tradeId, data }: { tradeId: number; data: TradeUpdateRequest }) =>
      updateTrade(tradeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio-holdings"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-trades"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-performance"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-allocation"] });
    },
  });
}

export function useDeleteTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tradeId: number) => deleteTrade(tradeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio-holdings"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-trades"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-performance"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-allocation"] });
    },
  });
}

export function useCSVDryRun() {
  return useMutation({
    mutationFn: (file: File) => uploadCSVDryRun(file),
  });
}

export function useCSVImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importCSV(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio-holdings"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-trades"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-performance"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio-allocation"] });
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

// --- Corporate Events Hooks (Phase 14) ---

export function useCorporateEvents(params?: { month?: string; type?: string; symbol?: string }) {
  return useQuery({
    queryKey: ["corporate-events", params?.month ?? "default", params?.type ?? "all", params?.symbol ?? "all"],
    queryFn: () => fetchCorporateEvents(params),
    staleTime: 10 * 60 * 1000, // 10 min — events change rarely
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
