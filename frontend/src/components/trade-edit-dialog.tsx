"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useUpdateTrade } from "@/lib/hooks";
import type { TradeResponse } from "@/lib/api";

interface TradeEditDialogProps {
  trade: TradeResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TradeEditDialog({ trade, open, onOpenChange }: TradeEditDialogProps) {
  const [side, setSide] = useState<"BUY" | "SELL">(trade.side as "BUY" | "SELL");
  const [quantity, setQuantity] = useState(String(trade.quantity));
  const [price, setPrice] = useState(String(trade.price));
  const [tradeDate, setTradeDate] = useState(trade.trade_date);
  const [fees, setFees] = useState(String(trade.fees));
  const [error, setError] = useState<string | null>(null);

  const mutation = useUpdateTrade();

  // Reset state when trade prop changes (dialog reopened with different trade)
  useEffect(() => {
    setSide(trade.side as "BUY" | "SELL");
    setQuantity(String(trade.quantity));
    setPrice(String(trade.price));
    setTradeDate(trade.trade_date);
    setFees(String(trade.fees));
    setError(null);
  }, [trade]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await mutation.mutateAsync({
        tradeId: trade.id,
        data: {
          side,
          quantity: parseInt(quantity, 10),
          price: parseFloat(price),
          trade_date: tradeDate,
          fees: parseFloat(fees) || 0,
        },
      });
      onOpenChange(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Lỗi không xác định";
      setError(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Sửa giao dịch</DialogTitle>
          <DialogDescription>
            Chỉnh sửa thông tin giao dịch. FIFO sẽ được tính lại tự động.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Symbol (read-only) */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Mã CK
            </label>
            <Input
              readOnly
              value={trade.symbol}
              className="bg-muted cursor-not-allowed font-mono"
            />
          </div>

          {/* Side toggle */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Loại
            </label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={side === "BUY" ? "default" : "outline"}
                size="sm"
                className={side === "BUY" ? "bg-[#26a69a] hover:bg-[#26a69a]/90 text-white" : ""}
                onClick={() => setSide("BUY")}
              >
                Mua
              </Button>
              <Button
                type="button"
                variant={side === "SELL" ? "default" : "outline"}
                size="sm"
                className={side === "SELL" ? "bg-[#ef5350] hover:bg-[#ef5350]/90 text-white" : ""}
                onClick={() => setSide("SELL")}
              >
                Bán
              </Button>
            </div>
          </div>

          {/* Quantity + Price */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Số lượng
              </label>
              <Input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="100"
                min={1}
                required
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Giá (VND)
              </label>
              <Input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="80000"
                min={0.01}
                step="any"
                required
                className="font-mono"
              />
            </div>
          </div>

          {/* Date + Fees */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Ngày GD
              </label>
              <Input
                type="date"
                value={tradeDate}
                onChange={(e) => setTradeDate(e.target.value)}
                required
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Phí (VND)
              </label>
              <Input
                type="number"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                placeholder="0"
                min={0}
                step="any"
                className="font-mono"
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-[#ef5350]">{error}</p>
          )}

          {/* Footer */}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className={
                side === "BUY"
                  ? "bg-[#26a69a] hover:bg-[#26a69a]/90 text-white"
                  : "bg-[#ef5350] hover:bg-[#ef5350]/90 text-white"
              }
            >
              {mutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
