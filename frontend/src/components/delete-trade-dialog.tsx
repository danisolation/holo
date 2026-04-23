"use client";

import type { TradeResponse } from "@/lib/api";
import { formatDateVN } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";

interface DeleteTradeDialogProps {
  trade: TradeResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isDeleting: boolean;
}

export function DeleteTradeDialog({
  trade,
  open,
  onOpenChange,
  onConfirm,
  isDeleting,
}: DeleteTradeDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xóa giao dịch?</DialogTitle>
          {trade && (
            <DialogDescription>
              Lệnh {trade.side === "BUY" ? "MUA" : "BÁN"} {trade.quantity} cổ{" "}
              {trade.ticker_symbol} ngày {formatDateVN(trade.trade_date)} sẽ bị
              xóa. Các lot liên quan sẽ được hoàn trả.
            </DialogDescription>
          )}
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Hủy
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting && <Loader2 className="size-4 animate-spin mr-2" />}
            Xóa lệnh
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
