"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RealtimePrice {
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  updated_at?: string;
  high?: number;
  low?: number;
  open?: number;
  ref_price?: number;
  ceiling?: number;
  floor?: number;
  bid_ask?: {
    symbol: string;
    bids: { price: number; volume: number }[];
    asks: { price: number; volume: number }[];
    match_price?: number;
    match_volume?: number;
    total_bid_volume?: number;
    total_ask_volume?: number;
  };
}

export type ConnectionStatus =
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "market_closed";

export interface UseRealtimePricesReturn {
  prices: Record<string, RealtimePrice>;
  status: ConnectionStatus;
  subscribedCount: number;
}

// ---------------------------------------------------------------------------
// WebSocket URL derivation
// ---------------------------------------------------------------------------

function deriveWsUrl(): string {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  // Strip trailing /api if present
  const base = apiBase.replace(/\/api\/?$/, "");
  // Replace http(s) with ws(s)
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/ws/prices`;
}

// ---------------------------------------------------------------------------
// VN Market hours guard: 9:00-15:00 UTC+7, Mon-Fri
// ---------------------------------------------------------------------------

const VN_UTC_OFFSET = 7;
const MARKET_OPEN_HOUR = 9;
const MARKET_CLOSE_HOUR = 15;
const MARKET_CHECK_INTERVAL = 60_000; // re-check every 60s

function isVNMarketOpen(): boolean {
  const now = new Date();
  const vnHour = (now.getUTCHours() + VN_UTC_OFFSET) % 24;
  const vnDay = new Date(
    now.getTime() + VN_UTC_OFFSET * 3600_000,
  ).getUTCDay();
  if (vnDay === 0 || vnDay === 6) return false;
  return vnHour >= MARKET_OPEN_HOUR && vnHour < MARKET_CLOSE_HOUR;
}

// ---------------------------------------------------------------------------
// Reconnect backoff: 1s → 2s → 4s → 8s → 16s → 30s max
// ---------------------------------------------------------------------------

const BACKOFF_BASE = 1000;
const BACKOFF_MAX = 30000;

function nextBackoff(attempt: number): number {
  return Math.min(BACKOFF_BASE * Math.pow(2, attempt), BACKOFF_MAX);
}

// ---------------------------------------------------------------------------
// Context — shared WebSocket connection across the app
// ---------------------------------------------------------------------------

interface RealtimePriceContextValue {
  prices: Record<string, RealtimePrice>;
  status: ConnectionStatus;
  subscribedSymbols: Set<string>;
  subscribe: (symbols: string[]) => void;
  unsubscribe: (symbols: string[]) => void;
}

const RealtimePriceContext = createContext<RealtimePriceContextValue | null>(
  null,
);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function RealtimePriceProvider({ children }: { children: ReactNode }) {
  const [prices, setPrices] = useState<Record<string, RealtimePrice>>({});
  const [status, _setStatus] = useState<ConnectionStatus>("disconnected");
  const statusRef = useRef<ConnectionStatus>("disconnected");
  const setStatus = useCallback((s: ConnectionStatus) => {
    statusRef.current = s;
    _setStatus(s);
  }, []);
  const subscribedSymbolsRef = useRef<Set<string>>(new Set());
  const [subscribedSymbols, setSubscribedSymbols] = useState<Set<string>>(
    new Set(),
  );
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  // Send subscribe message for current symbols
  const sendSubscribe = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const symbols = Array.from(subscribedSymbolsRef.current);
    if (symbols.length === 0) return;
    ws.send(JSON.stringify({ type: "subscribe", symbols }));
  }, []);

  // Connect / reconnect logic
  const connect = useCallback(() => {
    // Don't connect during SSR
    if (typeof window === "undefined") return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const url = deriveWsUrl();
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      setStatus("disconnected");
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      reconnectAttemptRef.current = 0;
      setStatus("connected");
      sendSubscribe();
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "price_update":
            setPrices((prev) => ({ ...prev, ...msg.data }));
            break;
          case "bid_ask_update":
            // Store bid/ask data alongside prices
            setPrices((prev) => {
              const updated = { ...prev };
              for (const [symbol, baData] of Object.entries(msg.data as Record<string, any>)) {
                updated[symbol] = {
                  ...updated[symbol],
                  bid_ask: baData,
                };
              }
              return updated;
            });
            break;
          case "heartbeat":
            // Keep-alive — no action needed
            break;
          case "market_status":
            if (msg.is_open === false) {
              setStatus("market_closed");
            } else if (statusRef.current === "market_closed") {
              setStatus("connected");
            }
            break;
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setStatus("reconnecting");
      const delay = nextBackoff(reconnectAttemptRef.current);
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // onerror is always followed by onclose, so let onclose handle reconnect
    };
  }, [sendSubscribe]);

  // Mount: establish connection only during market hours; Unmount: tear down
  useEffect(() => {
    mountedRef.current = true;

    function tick() {
      if (!mountedRef.current) return;
      if (isVNMarketOpen()) {
        // Market open — connect if not already connected
        if (!wsRef.current || wsRef.current.readyState > WebSocket.OPEN) {
          connect();
        }
      } else {
        // Market closed — disconnect if connected
        if (wsRef.current) {
          wsRef.current.onclose = null;
          wsRef.current.close();
          wsRef.current = null;
        }
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = null;
        }
        setStatus("market_closed");
      }
    }

    tick();
    const intervalId = setInterval(tick, MARKET_CHECK_INTERVAL);

    return () => {
      mountedRef.current = false;
      clearInterval(intervalId);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
    // Only run on mount/unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Subscribe/unsubscribe helpers
  const subscribe = useCallback(
    (symbols: string[]) => {
      let changed = false;
      for (const s of symbols) {
        const upper = s.toUpperCase();
        if (!subscribedSymbolsRef.current.has(upper)) {
          subscribedSymbolsRef.current.add(upper);
          changed = true;
        }
      }
      if (changed) {
        setSubscribedSymbols(new Set(subscribedSymbolsRef.current));
        sendSubscribe();
      }
    },
    [sendSubscribe],
  );

  const unsubscribe = useCallback((symbols: string[]) => {
    let changed = false;
    const removedSymbols: string[] = [];
    for (const s of symbols) {
      const upper = s.toUpperCase();
      if (subscribedSymbolsRef.current.has(upper)) {
        subscribedSymbolsRef.current.delete(upper);
        removedSymbols.push(upper);
        changed = true;
      }
    }
    if (changed) {
      setSubscribedSymbols(new Set(subscribedSymbolsRef.current));
      // Notify server to remove symbols from subscription set
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "unsubscribe", symbols: removedSymbols }));
      }
    }
  }, []);

  const value: RealtimePriceContextValue = {
    prices,
    status,
    subscribedSymbols,
    subscribe,
    unsubscribe,
  };

  return React.createElement(
    RealtimePriceContext.Provider,
    { value },
    children,
  );
}

// ---------------------------------------------------------------------------
// Hook — useRealtimePrices(symbols)
// ---------------------------------------------------------------------------

export function useRealtimePrices(symbols: string[]): UseRealtimePricesReturn {
  const ctx = useContext(RealtimePriceContext);

  // Stable symbol key for dependency tracking
  const symbolKey = symbols
    .map((s) => s.toUpperCase())
    .sort()
    .join(",");

  useEffect(() => {
    if (!ctx) return;
    const upperSymbols = symbols.map((s) => s.toUpperCase());
    if (upperSymbols.length > 0) {
      ctx.subscribe(upperSymbols);
    }
    return () => {
      if (upperSymbols.length > 0) {
        ctx.unsubscribe(upperSymbols);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbolKey]);

  if (!ctx) {
    return { prices: {}, status: "disconnected", subscribedCount: 0 };
  }

  return {
    prices: ctx.prices,
    status: ctx.status,
    subscribedCount: ctx.subscribedSymbols.size,
  };
}
