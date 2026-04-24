"use client";

import { CheckCircle2, ArrowRight, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatVND } from "@/lib/format";

export interface PostTradeCardProps {
  tickerSymbol: string;
  tickerName: string;
  quantity: number;
  price: number;
  stopLoss: number | null;
  takeProfit1: number | null;
  takeProfit2?: number | null;
  onDismiss: () => void;
  onViewJournal: () => void;
}

export function PostTradeCard({
  tickerSymbol,
  tickerName,
  quantity,
  price,
  stopLoss,
  takeProfit1,
  takeProfit2,
  onDismiss,
  onViewJournal,
}: PostTradeCardProps) {
  const totalValue = quantity * price;

  return (
    <Card className="border-[#26a69a]/30 bg-[#26a69a]/5">
      <CardContent className="pt-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-[#26a69a]" />
            <h3 className="font-bold text-[#26a69a]">Đã ghi nhận giao dịch</h3>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={onDismiss}
            aria-label="Đóng"
          >
            <X className="size-4" />
          </Button>
        </div>

        {/* Trade summary */}
        <div className="rounded-lg bg-background p-3 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Badge className="text-[#26a69a] bg-[#26a69a]/10">MUA</Badge>
            <span className="font-mono font-bold text-sm">{tickerSymbol}</span>
            <span className="text-sm text-muted-foreground">{tickerName}</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {quantity.toLocaleString()} cổ × {formatVND(price)}đ = {formatVND(totalValue)} VND
          </p>
        </div>

        {/* SL/TP monitoring */}
        {(stopLoss != null || takeProfit1 != null) && (
          <div className="rounded-lg border border-border p-3 mb-4">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              Theo dõi SL/TP
            </p>
            <div className="grid grid-cols-2 gap-y-1.5">
              {stopLoss != null && (
                <>
                  <span className="text-xs text-muted-foreground">Cắt lỗ (SL)</span>
                  <span className="font-mono text-sm font-bold text-right text-[#ef5350]">
                    {formatVND(stopLoss)}
                  </span>
                </>
              )}
              {takeProfit1 != null && (
                <>
                  <span className="text-xs text-muted-foreground">Chốt lời 1 (TP1)</span>
                  <span className="font-mono text-sm font-bold text-right text-[#26a69a]">
                    {formatVND(takeProfit1)}
                  </span>
                </>
              )}
              {takeProfit2 != null && (
                <>
                  <span className="text-xs text-muted-foreground">Chốt lời 2 (TP2)</span>
                  <span className="font-mono text-sm font-bold text-right text-[#26a69a]">
                    {formatVND(takeProfit2)}
                  </span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Next steps guidance */}
        <div className="space-y-2 mb-4">
          <p className="text-xs font-medium text-muted-foreground">Bước tiếp theo</p>
          <ol className="space-y-1.5 text-sm">
            {stopLoss != null && (
              <li className="flex items-start gap-2">
                <Badge variant="outline" className="mt-0.5 text-xs shrink-0">1</Badge>
                <span>Đặt lệnh cắt lỗ tại sàn: <span className="font-mono font-bold text-[#ef5350]">{formatVND(stopLoss)}</span></span>
              </li>
            )}
            {takeProfit1 != null && (
              <li className="flex items-start gap-2">
                <Badge variant="outline" className="mt-0.5 text-xs shrink-0">{stopLoss != null ? "2" : "1"}</Badge>
                <span>Chốt lời khi đạt mục tiêu: <span className="font-mono font-bold text-[#26a69a]">{formatVND(takeProfit1)}</span></span>
              </li>
            )}
            <li className="flex items-start gap-2">
              <Badge variant="outline" className="mt-0.5 text-xs shrink-0">
                {(stopLoss != null ? 1 : 0) + (takeProfit1 != null ? 1 : 0) + 1}
              </Badge>
              <span>Theo dõi vị thế trong tab <span className="font-bold">Nhật ký</span></span>
            </li>
          </ol>
        </div>

        {/* Action button */}
        <Button
          variant="outline"
          className="w-full"
          onClick={onViewJournal}
        >
          Xem nhật ký giao dịch
          <ArrowRight className="size-4 ml-2" />
        </Button>
      </CardContent>
    </Card>
  );
}
