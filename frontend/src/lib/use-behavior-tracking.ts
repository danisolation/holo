"use client";

import { useEffect } from "react";
import { postBehaviorEvent } from "@/lib/api";
import type { BehaviorEventCreate } from "@/lib/api";

const DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes per CONTEXT.md
const sentTimestamps = new Map<string, number>();

/**
 * Passive behavior event tracking hook. Fire-and-forget, no UI impact.
 * Per UI-SPEC: useEffect fires on mount, debounced per ticker per 5 min.
 * Errors are silently swallowed — no toast, no retry.
 */
export function useBehaviorTracking(
  eventType: BehaviorEventCreate["event_type"],
  tickerSymbol?: string
): void {
  useEffect(() => {
    if (!tickerSymbol) return;

    const key = `${eventType}:${tickerSymbol}`;
    const now = Date.now();
    const last = sentTimestamps.get(key) || 0;

    if (now - last < DEBOUNCE_MS) return;

    sentTimestamps.set(key, now);
    postBehaviorEvent({
      event_type: eventType,
      ticker_symbol: tickerSymbol,
    }).catch(() => {}); // Silent swallow per UI-SPEC
  }, [eventType, tickerSymbol]);
}
