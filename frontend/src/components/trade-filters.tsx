"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface TradeFiltersProps {
  ticker: string;
  onTickerChange: (value: string) => void;
  side: string; // "" | "BUY" | "SELL"
  onSideChange: (value: string) => void;
}

export function TradeFilters({
  ticker,
  onTickerChange,
  side,
  onSideChange,
}: TradeFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Input
        placeholder="Tìm mã..."
        className="w-40"
        value={ticker}
        onChange={(e) => onTickerChange(e.target.value)}
      />
      <Button
        variant={side === "" ? "default" : "outline"}
        size="sm"
        aria-pressed={side === ""}
        onClick={() => onSideChange("")}
      >
        Tất cả
      </Button>
      <Button
        variant={side === "BUY" ? "default" : "outline"}
        size="sm"
        aria-pressed={side === "BUY"}
        onClick={() => onSideChange("BUY")}
      >
        MUA
      </Button>
      <Button
        variant={side === "SELL" ? "default" : "outline"}
        size="sm"
        aria-pressed={side === "SELL"}
        onClick={() => onSideChange("SELL")}
      >
        BÁN
      </Button>
    </div>
  );
}
