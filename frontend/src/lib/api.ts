const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// --- Types matching backend Pydantic schemas ---

export interface Ticker {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  exchange: string;
  market_cap: number | null;
  is_active: boolean;
}

export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorData {
  ticker_symbol: string;
  date: string;
  rsi_14: number | null;
  macd_line: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_12: number | null;
  ema_26: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  // Phase 17: Volatility, Trend Strength, Momentum
  atr_14: number | null;
  adx_14: number | null;
  plus_di_14: number | null;
  minus_di_14: number | null;
  stoch_k_14: number | null;
  stoch_d_14: number | null;
  // Phase 18: Support & Resistance Levels
  pivot_point: number | null;
  support_1: number | null;
  support_2: number | null;
  resistance_1: number | null;
  resistance_2: number | null;
  fib_236: number | null;
  fib_382: number | null;
  fib_500: number | null;
  fib_618: number | null;
}

export interface AnalysisResult {
  ticker_symbol: string;
  analysis_type: string;
  analysis_date: string;
  signal: string;
  score: number;
  reasoning: string;
  model_version: string;
  raw_response?: Record<string, unknown> | null;
}

/** Phase 51: Structured combined analysis sections from raw_response */
export interface StructuredCombinedData {
  summary: string;
  key_levels: string;
  risks: string;
  action: string;
}

export interface AnalysisSummary {
  ticker_symbol: string;
  technical?: AnalysisResult;
  fundamental?: AnalysisResult;
  sentiment?: AnalysisResult;
  combined?: AnalysisResult;
  trading_signal?: AnalysisResult;  // Phase 20
}

export interface NewsArticleResponse {
  title: string;
  url: string;
  published_at: string;
}

// --- Phase 62: Rumor Types ---

export interface RumorPost {
  content: string;
  author_name: string;
  is_authentic: boolean;
  total_likes: number;
  total_replies: number;
  posted_at: string;
}

export interface RumorScoreData {
  symbol: string;
  scored_date: string | null;
  credibility_score: number | null;
  impact_score: number | null;
  direction: string | null;
  key_claims: string[];
  reasoning: string | null;
  posts: RumorPost[];
}

export interface WatchlistRumorSummary {
  symbol: string;
  rumor_count: number;
  avg_credibility: number | null;
  avg_impact: number | null;
  dominant_direction: string | null;
}

// --- Phase 49: Watchlist Types ---

export interface WatchlistItem {
  symbol: string;
  created_at: string;
  sector_group: string | null;  // Phase 54 — user-assigned or ICB auto-populated
  ai_signal: string | null;
  ai_score: number | null;
  signal_date: string | null;
  last_analysis_at: string | null;  // Phase 58: ISO timestamp of latest AI analysis
}

// --- Phase 20: Trading Plan Types ---

export interface TradingPlanDetail {
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  risk_reward_ratio: number;
  position_size_pct: number;
  timeframe: "swing" | "position";
}

export interface DirectionAnalysis {
  direction: "long" | "bearish";
  confidence: number;           // 1-10
  trading_plan: TradingPlanDetail;
  reasoning: string;            // Vietnamese text
}

export interface TickerTradingSignal {
  ticker: string;
  recommended_direction: "long" | "bearish";
  long_analysis: DirectionAnalysis;
  bearish_analysis: DirectionAnalysis;
}

// --- Phase 43: Daily Picks Types ---

export interface DailyPickResponse {
  id: number;
  pick_date: string;
  ticker_symbol: string;
  ticker_name: string;
  rank: number | null;
  composite_score: number;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  take_profit_2: number | null;
  risk_reward: number | null;
  position_size_shares: number | null;
  position_size_vnd: number | null;
  position_size_pct: number | null;
  explanation: string | null;
  status: "picked" | "almost";
  rejection_reason: string | null;
}

export interface DailyPicksResponse {
  date: string;
  capital: number;
  picks: DailyPickResponse[];
  almost_selected: DailyPickResponse[];
}

export interface ProfileResponse {
  capital: number;
  risk_level: number;
  broker_fee_pct: number;
}

export interface ProfileUpdate {
  capital: number;
  risk_level: number;
}

// --- API Error ---

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

// --- Fetch Functions ---

export async function fetchTickers(
  sector?: string,
  exchange?: string,
  limit?: number,
  offset?: number,
): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const qs = params.toString();
  return apiFetch<Ticker[]>(`/tickers/${qs ? `?${qs}` : ""}`);
}

export async function fetchPrices(
  symbol: string,
  days: number = 365,
): Promise<PriceData[]> {
  return apiFetch<PriceData[]>(
    `/tickers/${encodeURIComponent(symbol)}/prices?days=${days}`,
  );
}

export async function fetchIndicators(
  symbol: string,
  limit: number = 100,
  offset: number = 0,
): Promise<IndicatorData[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (offset > 0) params.set("offset", String(offset));
  return apiFetch<IndicatorData[]>(
    `/analysis/${encodeURIComponent(symbol)}/indicators?${params}`,
  );
}

export async function fetchAnalysisSummary(
  symbol: string,
): Promise<AnalysisSummary> {
  return apiFetch<AnalysisSummary>(
    `/analysis/${encodeURIComponent(symbol)}/summary`,
  );
}

export async function fetchTickerNews(
  symbol: string,
  limit: number = 10,
  offset: number = 0,
): Promise<NewsArticleResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (offset > 0) params.set("offset", String(offset));
  return apiFetch<NewsArticleResponse[]>(
    `/analysis/${encodeURIComponent(symbol)}/news?${params}`,
  );
}

export async function fetchTradingSignal(
  symbol: string,
): Promise<TickerTradingSignal | null> {
  try {
    const result = await apiFetch<
      AnalysisResult & { raw_response?: TickerTradingSignal }
    >(`/analysis/${encodeURIComponent(symbol)}/trading-signal`);
    return result.raw_response ?? null;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// --- Market Overview (heatmap data) ---

export interface MarketTicker {
  symbol: string;
  name: string;
  sector: string | null;
  exchange: string;
  market_cap: number | null;
  last_price: number | null;
  change_pct: number | null;
}

export interface MarketOverviewParams {
  exchange?: string;
  sort?: "change_pct" | "market_cap" | "symbol";
  order?: "desc" | "asc";
  top?: number;
}

export async function fetchMarketOverview(params?: MarketOverviewParams): Promise<MarketTicker[]> {
  const searchParams = new URLSearchParams();
  if (params?.exchange && params.exchange !== "all") {
    searchParams.set("exchange", params.exchange);
  }
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.order) searchParams.set("order", params.order);
  if (params?.top) searchParams.set("top", String(params.top));
  const qs = searchParams.toString();
  return apiFetch<MarketTicker[]>(`/tickers/market-overview${qs ? `?${qs}` : ""}`);
}

export async function triggerOnDemandAnalysis(symbol: string): Promise<{ message: string; triggered: boolean }> {
  return apiFetch<{ message: string; triggered: boolean }>(
    `/analysis/${encodeURIComponent(symbol)}/analyze-now`,
    { method: "POST" },
  );
}

// --- Health Types ---

export interface JobStatusItem {
  job_id: string;
  job_name: string;
  status: string;
  color: "green" | "yellow" | "red";
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  result_summary: Record<string, unknown> | null;
  error_message: string | null;
}

export interface JobStatusResponse {
  jobs: JobStatusItem[];
}

export interface DataFreshnessItem {
  data_type: string;
  table_name: string;
  latest: string | null;
  is_stale: boolean;
  threshold_hours: number;
}

export interface DataFreshnessResponse {
  items: DataFreshnessItem[];
}

export interface ErrorRateDayItem {
  day: string;
  total: number;
  failed: number;
}

export interface ErrorRateJobItem {
  job_id: string;
  job_name: string;
  days: ErrorRateDayItem[];
  total_runs: number;
  total_failures: number;
}

export interface ErrorRateResponse {
  jobs: ErrorRateJobItem[];
}

export interface DbPoolResponse {
  pool_size: number;
  checked_in: number;
  checked_out: number;
  overflow: number;
  max_overflow: number;
}

export interface TriggerResponse {
  message: string;
  triggered: boolean;
}

export interface HealthSummary {
  status: "healthy" | "warning" | "degraded";
  jobs_total: number;
  jobs_healthy: number;
  jobs_warning: number;
  jobs_error: number;
  data_sources_total: number;
  data_sources_stale: number;
  pool_checked_out: number;
  pool_available: number;
}

// --- Health Fetch Functions ---

export async function fetchJobStatuses(): Promise<JobStatusResponse> {
  return apiFetch<JobStatusResponse>("/health/jobs");
}

export async function fetchDataFreshness(): Promise<DataFreshnessResponse> {
  return apiFetch<DataFreshnessResponse>("/health/data-freshness");
}

export async function fetchErrorRates(): Promise<ErrorRateResponse> {
  return apiFetch<ErrorRateResponse>("/health/errors");
}

export async function fetchDbPool(): Promise<DbPoolResponse> {
  return apiFetch<DbPoolResponse>("/health/db-pool");
}

export async function fetchHealthSummary(): Promise<HealthSummary> {
  return apiFetch<HealthSummary>("/health/summary");
}

export async function triggerJob(jobName: string): Promise<TriggerResponse> {
  return apiFetch<TriggerResponse>(
    `/health/trigger/${encodeURIComponent(jobName)}`,
    { method: "POST" }
  );
}

// --- Gemini Usage Types (Phase 15) ---

export interface GeminiUsageTodayBreakdown {
  analysis_type: string;
  requests: number;
  tokens: number;
}

export interface GeminiUsageToday {
  requests: number;
  tokens: number;
  limit_requests: number;
  limit_tokens: number;
  breakdown: GeminiUsageTodayBreakdown[];
}

export interface GeminiUsageDaily {
  date: string;
  tokens: number;
  requests: number;
}

export interface GeminiUsageResponse {
  today: GeminiUsageToday;
  daily: GeminiUsageDaily[];
}

// --- Pipeline Timeline Types (Phase 15) ---

export interface PipelineStep {
  job_id: string;
  job_name: string;
  started_at: string;
  duration_seconds: number | null;
  status: string;
}

export interface PipelineRun {
  date: string;
  total_seconds: number;
  steps: PipelineStep[];
}

export interface PipelineTimelineResponse {
  runs: PipelineRun[];
}

// --- Gemini Usage & Pipeline Timeline Fetch Functions (Phase 15) ---

export async function fetchGeminiUsage(days: number = 7): Promise<GeminiUsageResponse> {
  return apiFetch<GeminiUsageResponse>(`/health/gemini-usage?days=${days}`);
}

export async function fetchPipelineTimeline(days: number = 7): Promise<PipelineTimelineResponse> {
  return apiFetch<PipelineTimelineResponse>(`/health/pipeline-timeline?days=${days}`);
}

// --- Phase 45: Pick Performance Types ---

export interface PickPerformanceResponse {
  win_rate: number;
  total_pnl: number;
  avg_risk_reward: number;
  current_streak: number;
  total_closed: number;
  total_winners: number;
  total_losers: number;
}

export interface PickHistoryItem {
  id: number;
  pick_date: string;
  ticker_symbol: string;
  rank: number | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit_1: number | null;
  pick_outcome: string;
  actual_return_pct: number | null;
  days_held: number | null;
  has_trades: boolean;
}

export interface PickHistoryResponse {
  items: PickHistoryItem[];
  total: number;
  page: number;
  per_page: number;
}

// --- Phase 43: Daily Picks API ---

export async function fetchDailyPicks(): Promise<DailyPicksResponse> {
  return apiFetch<DailyPicksResponse>("/picks/today");
}

export async function fetchPickHistory(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}): Promise<PickHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.status && params.status !== "all") searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return apiFetch<PickHistoryResponse>(`/picks/history${qs ? `?${qs}` : ""}`);
}

export async function fetchPickPerformance(): Promise<PickPerformanceResponse> {
  return apiFetch<PickPerformanceResponse>("/picks/performance");
}

export async function fetchProfile(): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile");
}

export async function updateProfile(data: ProfileUpdate): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>("/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// --- Phase 44: Trade Journal Types ---

export interface TradeResponse {
  id: number;
  ticker_symbol: string;
  ticker_name: string;
  daily_pick_id: number | null;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  broker_fee: number;
  sell_tax: number;
  total_fee: number;
  gross_pnl: number | null;
  net_pnl: number | null;
  trade_date: string;
  user_notes: string | null;
  created_at: string;
}

export interface TradeStatsResponse {
  total_trades: number;
  realized_gross_pnl: number;
  realized_net_pnl: number;
  open_positions: number;
}

export interface TradesListResponse {
  trades: TradeResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TradeCreate {
  ticker_symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  trade_date: string;
  user_notes?: string;
  daily_pick_id?: number | null;
  broker_fee_override?: number;
  sell_tax_override?: number;
}

// --- Phase 44: Trade Journal Fetch Functions ---

export async function fetchTrades(params?: {
  page?: number;
  ticker?: string;
  side?: string;
  sort?: string;
  order?: string;
}): Promise<TradesListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.ticker) searchParams.set("ticker", params.ticker);
  if (params?.side) searchParams.set("side", params.side);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.order) searchParams.set("order", params.order);
  const qs = searchParams.toString();
  return apiFetch<TradesListResponse>(`/trades${qs ? `?${qs}` : ""}`);
}

export async function fetchTradeStats(): Promise<TradeStatsResponse> {
  return apiFetch<TradeStatsResponse>("/trades/stats");
}

export async function createTrade(data: TradeCreate): Promise<TradeResponse> {
  return apiFetch<TradeResponse>("/trades", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTrade(id: number): Promise<void> {
  await apiFetch<void>(`/trades/${id}`, { method: "DELETE" });
}

// --- Phase 46: Behavior Tracking Types & API ---

export interface RiskSuggestionResponse {
  id: number;
  current_level: number;
  suggested_level: number;
  reason: string;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
}

export interface RiskSuggestionRespondRequest {
  action: "accept" | "reject";
}

export interface HabitDetection {
  habit_type: "premature_sell" | "holding_losers" | "impulsive_trade";
  count: number;
  latest_ticker: string | null;
  latest_date: string | null;
}

export interface HabitDetectionsResponse {
  habits: HabitDetection[];
  analysis_date: string | null;
}

export interface ViewingStatItem {
  ticker_symbol: string;
  sector: string | null;
  view_count: number;
  last_viewed: string;
}

export interface ViewingStatsResponse {
  items: ViewingStatItem[];
  total_views: number;
}

export interface SectorPreference {
  sector: string;
  total_trades: number;
  win_count: number;
  loss_count: number;
  net_pnl: number;
  win_rate: number;
  preference_score: number;
}

export interface SectorPreferencesResponse {
  sectors: SectorPreference[];
  insufficient_count: number;
}

export interface BehaviorEventCreate {
  event_type: "ticker_view" | "search_click" | "pick_click";
  ticker_symbol?: string;
  metadata?: Record<string, unknown>;
}

export async function fetchRiskSuggestion(): Promise<RiskSuggestionResponse | null> {
  return apiFetch<RiskSuggestionResponse | null>("/behavior/risk-suggestion");
}

export async function respondRiskSuggestion(
  id: number,
  data: RiskSuggestionRespondRequest
): Promise<RiskSuggestionResponse> {
  return apiFetch<RiskSuggestionResponse>(
    `/behavior/risk-suggestion/${id}/respond`,
    { method: "POST", body: JSON.stringify(data) }
  );
}

export async function fetchHabitDetections(): Promise<HabitDetectionsResponse> {
  return apiFetch<HabitDetectionsResponse>("/behavior/habits");
}

export async function fetchViewingStats(): Promise<ViewingStatsResponse> {
  return apiFetch<ViewingStatsResponse>("/behavior/viewing-stats");
}

export async function fetchSectorPreferences(): Promise<SectorPreferencesResponse> {
  return apiFetch<SectorPreferencesResponse>("/behavior/sector-preferences");
}

export async function postBehaviorEvent(data: BehaviorEventCreate): Promise<void> {
  await fetch(`${API_BASE}/behavior/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  // Fire-and-forget: don't check res.ok, don't throw
}

// --- Phase 47: Goals & Weekly Reviews Types ---

export interface GoalResponse {
  id: number;
  target_pnl: number;
  actual_pnl: number;
  month: string;               // "2026-04-01"
  status: "active" | "completed" | "missed";
  progress_pct: number;        // e.g. 50.0
  progress_color: string;      // "green" | "amber" | "red"
  created_at: string;
  updated_at: string;
}

export interface WeeklyPromptResponse {
  id: number;
  week_start: string;
  prompt_type: "risk_tolerance";
  response: string | null;     // null = pending
  risk_level_before: number;
  risk_level_after: number | null;
  created_at: string;
}

export interface WeeklyReviewResponse {
  id: number;
  week_start: string;
  week_end: string;
  summary_text: string;
  highlights: { good: string[]; bad: string[] };
  suggestions: string[];
  trades_count: number;
  win_count: number;
  total_pnl: number;
  created_at: string;
}

// --- Phase 47: Goals & Weekly Reviews Fetch Functions ---

export async function fetchCurrentGoal(): Promise<GoalResponse | null> {
  return apiFetch<GoalResponse | null>("/goals/current");
}

export async function setGoal(target_pnl: number): Promise<GoalResponse> {
  return apiFetch<GoalResponse>("/goals", {
    method: "POST",
    body: JSON.stringify({ target_pnl }),
  });
}

export async function fetchWeeklyPrompt(): Promise<WeeklyPromptResponse | null> {
  return apiFetch<WeeklyPromptResponse | null>("/goals/weekly-prompt");
}

export async function respondWeeklyPrompt(
  id: number,
  response: string,
): Promise<WeeklyPromptResponse> {
  return apiFetch<WeeklyPromptResponse>(
    `/goals/weekly-prompt/${id}/respond`,
    { method: "POST", body: JSON.stringify({ response }) },
  );
}

export async function fetchLatestReview(): Promise<WeeklyReviewResponse | null> {
  return apiFetch<WeeklyReviewResponse | null>("/goals/weekly-review");
}

// --- Phase 49: Watchlist API ---

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/watchlist");
}

export async function addWatchlistItem(symbol: string): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>("/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol }),
  });
}

export async function removeWatchlistItem(symbol: string): Promise<void> {
  await apiFetch<void>(`/watchlist/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

export async function migrateWatchlist(symbols: string[]): Promise<WatchlistItem[]> {
  return apiFetch<WatchlistItem[]>("/watchlist/migrate", {
    method: "POST",
    body: JSON.stringify({ symbols }),
  });
}

// --- Phase 54: Sector Group API ---

export async function updateWatchlistSector(
  symbol: string,
  sectorGroup: string | null
): Promise<WatchlistItem> {
  return apiFetch<WatchlistItem>(`/watchlist/${encodeURIComponent(symbol)}`, {
    method: "PATCH",
    body: JSON.stringify({ sector_group: sectorGroup }),
  });
}

export async function fetchSectors(): Promise<string[]> {
  return apiFetch<string[]>("/tickers/sectors");
}

// --- Phase 55: Discovery Types & API ---

export interface DiscoveryItem {
  symbol: string;
  name: string;
  sector: string | null;
  score_date: string;
  rsi_score: number | null;
  macd_score: number | null;
  adx_score: number | null;
  volume_score: number | null;
  pe_score: number | null;
  roe_score: number | null;
  total_score: number;
  dimensions_scored: number;
}

export async function fetchDiscovery(params?: {
  sector?: string;
  signal_type?: string;
  min_score?: number;
  limit?: number;
}): Promise<DiscoveryItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.sector) searchParams.set("sector", params.sector);
  if (params?.signal_type) searchParams.set("signal_type", params.signal_type);
  if (params?.min_score !== undefined) searchParams.set("min_score", String(params.min_score));
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return apiFetch<DiscoveryItem[]>(`/discovery${qs ? `?${qs}` : ""}`);
}

// --- Phase 62: Rumor API ---

export async function fetchRumorScores(symbol: string): Promise<RumorScoreData> {
  return apiFetch<RumorScoreData>(`/rumors/${encodeURIComponent(symbol)}`);
}

export async function fetchWatchlistRumors(): Promise<WatchlistRumorSummary[]> {
  return apiFetch<WatchlistRumorSummary[]>("/rumors/watchlist/summary");
}

// --- Phase 65: Accuracy API ---

export interface AccuracyStats {
  total: number;
  correct?: number;
  overall_accuracy_pct: number;
  by_direction: Record<string, { total: number; correct: number; accuracy_pct: number }>;
  by_timeframe?: Record<string, { total: number; correct: number; accuracy_pct: number }>;
  period_days: number;
}

export interface TickerAccuracyHistory {
  date: string;
  predicted: string;
  confidence: number;
  pct_change_7d: number | null;
  verdict: string | null;
}

export interface TickerAccuracy {
  total: number;
  correct: number;
  accuracy_pct: number;
  history: TickerAccuracyHistory[];
}

export async function fetchAccuracyStats(days: number = 30): Promise<AccuracyStats> {
  return apiFetch<AccuracyStats>(`/accuracy/stats?days=${days}`);
}

export async function fetchTickerAccuracy(tickerId: number, days: number = 30): Promise<TickerAccuracy> {
  return apiFetch<TickerAccuracy>(`/accuracy/ticker/${tickerId}?days=${days}`);
}
