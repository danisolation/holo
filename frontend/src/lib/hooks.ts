"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchTickers,
  fetchPrices,
  fetchIndicators,
  fetchAnalysisSummary,
  fetchTradingSignal,
  fetchMarketOverview,
  triggerOnDemandAnalysis,
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

// --- Trading Signal Hook (Phase 20) ---

export function useTradingSignal(symbol: string | undefined) {
  return useQuery({
    queryKey: ["trading-signal", symbol],
    queryFn: () => fetchTradingSignal(symbol!),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
  });
}
