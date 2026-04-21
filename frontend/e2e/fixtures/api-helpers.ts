import { APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8001/api';

export class ApiHelpers {
  constructor(private request: APIRequestContext) {}

  /** Check if API is healthy */
  async healthCheck() {
    const response = await this.request.get(`${API_BASE}/health`);
    return response.ok();
  }

  /** Get tickers list */
  async getTickers() {
    const response = await this.request.get(`${API_BASE}/tickers`);
    return response.json();
  }

  /** Get a specific ticker's price data */
  async getTickerPrices(symbol: string) {
    const response = await this.request.get(`${API_BASE}/tickers/${symbol}/prices`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get analysis summary for a ticker */
  async getAnalysis(symbol: string) {
    const response = await this.request.get(`${API_BASE}/analysis/${symbol}/summary`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trading config */
  async getPaperSettings() {
    const response = await this.request.get(`${API_BASE}/paper-trading/config`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trades list */
  async getPaperTrades() {
    const response = await this.request.get(`${API_BASE}/paper-trading/trades`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trading analytics summary */
  async getPaperAnalytics() {
    const response = await this.request.get(`${API_BASE}/paper-trading/analytics/summary`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get watchlist (client-side feature — endpoint for future use) */
  async getWatchlist() {
    const response = await this.request.get(`${API_BASE}/watchlist`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }
}
