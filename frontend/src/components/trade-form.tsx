"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useCreateTrade } from "@/lib/hooks";

export function TradeForm() {
  const [open, setOpen] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [tradeDate, setTradeDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [fees, setFees] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useCreateTrade();

  const resetForm = () => {
    setSymbol("");
    setSide("BUY");
    setQuantity("");
    setPrice("");
    setTradeDate(new Date().toISOString().split("T")[0]);
    setFees("");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await mutation.mutateAsync({
        symbol: symbol.toUpperCase(),
        side,
        quantity: parseInt(quantity, 10),
        price: parseFloat(price),
        trade_date: tradeDate,
        fees: fees ? parseFloat(fees) : 0,
      });
      resetForm();
      setOpen(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Lỗi không xác định";
      setError(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button size="sm">
            <Plus className="size-4 mr-1" />
            Thêm giao dịch
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Thêm giao dịch</DialogTitle>
          <DialogDescription>
            Nhập thông tin mua hoặc bán cổ phiếu
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Symbol */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              Mã CK
            </label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="VNM"
              required
              className="font-mono uppercase"
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

          {/* Submit */}
          <DialogFooter>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className={
                side === "BUY"
                  ? "bg-[#26a69a] hover:bg-[#26a69a]/90 text-white"
                  : "bg-[#ef5350] hover:bg-[#ef5350]/90 text-white"
              }
            >
              {mutation.isPending
                ? "Đang xử lý..."
                : side === "BUY"
                  ? "Xác nhận Mua"
                  : "Xác nhận Bán"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
