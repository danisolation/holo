"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatVND, formatDateVN } from "@/lib/format";
import { useSimulatorTrades } from "@/lib/hooks";
import { TradeReviewPanel } from "./trade-review-panel";

const SOURCE_FILTERS = [
  { label: "Tất cả", value: undefined },
  { label: "AI", value: "ai_auto" },
  { label: "Thủ công", value: "manual" },
] as const;

export function TradeHistory({ portfolioType = "user" }: { portfolioType?: string }) {
  const [page, setPage] = useState(1);
  const [source, setSource] = useState<string | undefined>(undefined);
  const { data, isLoading } = useSimulatorTrades(page, source, portfolioType);

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  return (
    <div className="space-y-4">
      {/* Source filter tabs */}
      <div className="flex gap-2">
        {SOURCE_FILTERS.map((f) => (
          <Button
            key={f.label}
            variant={source === f.value ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setSource(f.value);
              setPage(1);
            }}
          >
            {f.label}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          Đang tải...
        </p>
      ) : !data || data.trades.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          Chưa có giao dịch nào
        </p>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ngày</TableHead>
                <TableHead>Mã CK</TableHead>
                <TableHead>Hướng</TableHead>
                <TableHead className="text-right">SL</TableHead>
                <TableHead className="text-right">Giá</TableHead>
                <TableHead className="text-right">Phí</TableHead>
                <TableHead className="text-right">Thuế</TableHead>
                <TableHead className="text-right">Lãi/Lỗ</TableHead>
                <TableHead>Nguồn</TableHead>
                <TableHead>Lý do</TableHead>
                <TableHead>Review</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.trades.map((t) => {
                const pnlColor =
                  t.net_pnl !== null
                    ? t.net_pnl >= 0
                      ? "var(--trading-bull)"
                      : "var(--trading-bear)"
                    : undefined;
                return (
                  <TableRow key={t.id}>
                    <TableCell>{formatDateVN(t.trade_date)}</TableCell>
                    <TableCell className="font-medium">
                      {t.ticker_symbol}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={
                          t.side === "BUY"
                            ? "bg-trading-bull/20 text-trading-bull"
                            : "bg-trading-bear/20 text-trading-bear"
                        }
                      >
                        {t.side === "BUY" ? "MUA" : "BÁN"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {t.quantity.toLocaleString("vi-VN")}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatVND(t.price)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatVND(t.broker_fee)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatVND(t.sell_tax)}
                    </TableCell>
                    <TableCell
                      className="text-right"
                      style={{ color: pnlColor }}
                    >
                      {t.net_pnl !== null
                        ? `${t.net_pnl >= 0 ? "+" : ""}${formatVND(t.net_pnl)}`
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {t.source === "ai_auto" ? "AI" : "Thủ công"}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[200px]">
                      {t.rationale ? (
                        <span className="text-xs text-muted-foreground line-clamp-2" title={t.rationale}>
                          {t.rationale}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {t.side === "SELL" ? (
                        <TradeReviewPanel tradeId={t.id} portfolioType={portfolioType} />
                      ) : null}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Trang {data.page}/{totalPages} — {data.total} giao dịch
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Trước
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Sau
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
