"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCreateSimulatorTrade } from "@/lib/hooks";
import type { SimulatorTradeCreate } from "@/lib/api";

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function TradeForm() {
  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [tradeDate, setTradeDate] = useState(todayStr);
  const [notes, setNotes] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const mutation = useCreateSimulatorTrade();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccessMsg("");

    const data: SimulatorTradeCreate = {
      ticker_symbol: ticker.toUpperCase().trim(),
      side,
      quantity: Number(quantity),
      price: Number(price),
      trade_date: tradeDate,
      source: "manual",
      user_notes: notes.trim() || null,
    };

    mutation.mutate(data, {
      onSuccess: () => {
        setTicker("");
        setQuantity("");
        setPrice("");
        setNotes("");
        setTradeDate(todayStr());
        setSuccessMsg("Tạo lệnh thành công!");
        setTimeout(() => setSuccessMsg(""), 3000);
      },
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      {/* Mã CK */}
      <div>
        <label className="text-sm font-medium mb-1 block">Mã CK</label>
        <Input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="VD: VNM"
          required
        />
      </div>

      {/* Hướng */}
      <div>
        <label className="text-sm font-medium mb-1 block">Hướng</label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant={side === "BUY" ? "default" : "outline"}
            onClick={() => setSide("BUY")}
            className={side === "BUY" ? "bg-trading-bull hover:bg-trading-bull/80 text-white" : ""}
          >
            MUA
          </Button>
          <Button
            type="button"
            variant={side === "SELL" ? "default" : "outline"}
            onClick={() => setSide("SELL")}
            className={side === "SELL" ? "bg-trading-bear hover:bg-trading-bear/80 text-white" : ""}
          >
            BÁN
          </Button>
        </div>
      </div>

      {/* Số lượng + Giá */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium mb-1 block">Số lượng</label>
          <Input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="100"
            min={1}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">Giá</label>
          <Input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="50000"
            min={0}
            step="any"
            required
          />
        </div>
      </div>

      {/* Ngày */}
      <div>
        <label className="text-sm font-medium mb-1 block">Ngày</label>
        <Input
          type="date"
          value={tradeDate}
          onChange={(e) => setTradeDate(e.target.value)}
          required
        />
      </div>

      {/* Ghi chú */}
      <div>
        <label className="text-sm font-medium mb-1 block">Ghi chú</label>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Ghi chú (tuỳ chọn)"
          rows={2}
        />
      </div>

      {/* Error */}
      {mutation.error && (
        <p className="text-sm" style={{ color: "var(--trading-bear)" }}>
          {mutation.error.message}
        </p>
      )}

      {/* Success */}
      {successMsg && (
        <p className="text-sm" style={{ color: "var(--trading-bull)" }}>
          {successMsg}
        </p>
      )}

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Đang xử lý..." : "Tạo lệnh"}
      </Button>
    </form>
  );
}
