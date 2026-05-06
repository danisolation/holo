"use client";

import type { RealtimePrice } from "@/lib/use-realtime-prices";

interface BidAskPanelProps {
  data: RealtimePrice["bid_ask"];
  refPrice?: number;
}

export function BidAskPanel({ data, refPrice }: BidAskPanelProps) {
  if (!data || !data.bids || !data.asks) {
    return (
      <div className="text-sm text-muted-foreground text-center py-4">
        Chưa có dữ liệu Bid/Ask
      </div>
    );
  }

  const maxVolume = Math.max(
    ...data.bids.map((b) => b.volume),
    ...data.asks.map((a) => a.volume),
    1
  );

  const spread = data.asks[0]?.price && data.bids[0]?.price
    ? data.asks[0].price - data.bids[0].price
    : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
        <span>Bid (Mua)</span>
        <span>Giá</span>
        <span>Ask (Bán)</span>
      </div>

      {/* Ask levels (reversed — best ask at bottom) */}
      {[...data.asks].reverse().map((ask, i) => (
        <div key={`ask-${i}`} className="flex items-center gap-2 h-7">
          <div className="w-20" />
          <div className="flex-1 relative h-5 flex items-center justify-end">
            <div
              className="absolute right-0 top-0 h-full bg-red-500/15 rounded-sm"
              style={{ width: `${(ask.volume / maxVolume) * 100}%` }}
            />
            <span className="relative text-xs font-mono text-muted-foreground pr-1">
              {ask.volume > 0 ? (ask.volume / 10).toLocaleString("vi-VN") : "—"}
            </span>
          </div>
          <div className="w-20 text-center">
            <span className="text-xs font-mono text-[#ef5350] font-medium">
              {ask.price > 0 ? (ask.price / 1000).toFixed(1) : "—"}
            </span>
          </div>
          <div className="flex-1" />
          <div className="w-20" />
        </div>
      ))}

      {/* Spread indicator */}
      {spread !== null && spread > 0 && (
        <div className="flex items-center justify-center py-1">
          <span className="text-[10px] text-muted-foreground bg-muted/50 px-2 py-0.5 rounded">
            Spread: {(spread / 1000).toFixed(1)}
          </span>
        </div>
      )}

      {/* Bid levels (best bid at top) */}
      {data.bids.map((bid, i) => (
        <div key={`bid-${i}`} className="flex items-center gap-2 h-7">
          <div className="w-20" />
          <div className="flex-1" />
          <div className="w-20 text-center">
            <span className="text-xs font-mono text-[#26a69a] font-medium">
              {bid.price > 0 ? (bid.price / 1000).toFixed(1) : "—"}
            </span>
          </div>
          <div className="flex-1 relative h-5 flex items-center">
            <div
              className="absolute left-0 top-0 h-full bg-green-500/15 rounded-sm"
              style={{ width: `${(bid.volume / maxVolume) * 100}%` }}
            />
            <span className="relative text-xs font-mono text-muted-foreground pl-1">
              {bid.volume > 0 ? (bid.volume / 10).toLocaleString("vi-VN") : "—"}
            </span>
          </div>
          <div className="w-20" />
        </div>
      ))}

      {/* Total volumes */}
      <div className="flex items-center justify-between text-[10px] text-muted-foreground border-t border-border/50 pt-1 mt-2">
        <span>
          Tổng mua:{" "}
          <span className="text-[#26a69a] font-mono">
            {data.total_bid_volume ? (data.total_bid_volume / 10).toLocaleString("vi-VN") : "—"}
          </span>
        </span>
        <span>
          Tổng bán:{" "}
          <span className="text-[#ef5350] font-mono">
            {data.total_ask_volume ? (data.total_ask_volume / 10).toLocaleString("vi-VN") : "—"}
          </span>
        </span>
      </div>
    </div>
  );
}
