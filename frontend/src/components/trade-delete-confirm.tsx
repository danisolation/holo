"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteTrade } from "@/lib/hooks";
import type { TradeResponse } from "@/lib/api";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

interface TradeDeleteConfirmProps {
  trade: TradeResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TradeDeleteConfirm({ trade, open, onOpenChange }: TradeDeleteConfirmProps) {
  const [error, setError] = useState<string | null>(null);
  const mutation = useDeleteTrade();

  const handleDelete = async () => {
    setError(null);
    try {
      await mutation.mutateAsync(trade.id);
      onOpenChange(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Lỗi không xác định";
      setError(message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Xóa giao dịch</DialogTitle>
          <DialogDescription>
            Bạn có chắc muốn xóa giao dịch này? FIFO sẽ được tính lại cho mã {trade.symbol}.
          </DialogDescription>
        </DialogHeader>

        {/* Trade summary */}
        <div className="bg-muted rounded-lg p-3 space-y-1">
          <div className="flex items-center gap-2">
            <Badge
              variant="secondary"
              className={
                trade.side === "BUY"
                  ? "text-[#26a69a] bg-[#26a69a]/10"
                  : "text-[#ef5350] bg-[#ef5350]/10"
              }
            >
              {trade.side === "BUY" ? "Mua" : "Bán"}
            </Badge>
            <span className="font-bold">{trade.symbol}</span>
            <span className="text-sm text-muted-foreground">{trade.quantity} CP</span>
          </div>
          <div className="font-mono text-sm">
            {formatVND(trade.price)} ₫ × {trade.quantity} = {formatVND(trade.price * trade.quantity)} ₫
          </div>
          <div className="text-xs text-muted-foreground">
            Ngày: {trade.trade_date}
          </div>
        </div>

        {/* Error */}
        {error && (
          <p className="text-xs text-[#ef5350]">{error}</p>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={mutation.isPending}
            onClick={handleDelete}
          >
            {mutation.isPending ? "Đang xóa..." : "Xóa giao dịch"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
