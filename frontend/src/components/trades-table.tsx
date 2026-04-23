"use client";

import type { TradeResponse } from "@/lib/api";
import { formatVND, formatDateVN } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { ArrowUpDown, BookOpen, Sparkles, Trash2 } from "lucide-react";

interface TradesTableProps {
  trades: TradeResponse[];
  total: number;
  page: number;
  pageSize: number;
  sort: string;
  order: string;
  onSortChange: (sort: string, order: string) => void;
  onPageChange: (page: number) => void;
  onDelete: (trade: TradeResponse) => void;
  onCreateFirst?: () => void;
  isLoading: boolean;
}

function renderPnl(value: number | null, side: string) {
  if (side === "BUY" || value === null) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (value > 0) {
    return (
      <span className="text-[#26a69a] font-mono text-sm font-bold">
        ▲ +{formatVND(value)}
      </span>
    );
  }
  if (value < 0) {
    return (
      <span className="text-[#ef5350] font-mono text-sm font-bold">
        ▼ -{formatVND(Math.abs(value))}
      </span>
    );
  }
  return (
    <span className="text-muted-foreground font-mono text-sm font-bold">0</span>
  );
}

type SortableColumn = "trade_date" | "side" | "net_pnl";

function getAriaSortValue(
  column: SortableColumn,
  currentSort: string,
  currentOrder: string,
): "ascending" | "descending" | "none" {
  if (currentSort !== column) return "none";
  return currentOrder === "asc" ? "ascending" : "descending";
}

export function TradesTable({
  trades,
  total,
  page,
  pageSize,
  sort,
  order,
  onSortChange,
  onPageChange,
  onDelete,
  onCreateFirst,
  isLoading,
}: TradesTableProps) {
  const totalPages = Math.ceil(total / pageSize);
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  const handleSort = (column: SortableColumn) => {
    if (sort === column) {
      onSortChange(column, order === "asc" ? "desc" : "asc");
    } else {
      onSortChange(column, "desc");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <div className="p-4 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 rounded" />
          ))}
        </div>
      </Card>
    );
  }

  if (trades.length === 0) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
          <BookOpen className="size-12 text-muted-foreground/40" />
          <p className="text-lg font-bold mt-4">Chưa có giao dịch nào</p>
          <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
            Ghi lệnh mua/bán đầu tiên để bắt đầu theo dõi lãi lỗ.
          </p>
          {onCreateFirst && (
            <Button className="mt-4" onClick={onCreateFirst}>
              Ghi lệnh đầu tiên
            </Button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                className="w-28 cursor-pointer select-none"
                aria-sort={getAriaSortValue("trade_date", sort, order)}
                onClick={() => handleSort("trade_date")}
              >
                <span className="inline-flex items-center gap-1">
                  Ngày
                  <ArrowUpDown className="size-3 text-muted-foreground" />
                </span>
              </TableHead>
              <TableHead className="w-20">Mã</TableHead>
              <TableHead
                className="w-16 text-center cursor-pointer select-none"
                aria-sort={getAriaSortValue("side", sort, order)}
                onClick={() => handleSort("side")}
              >
                <span className="inline-flex items-center gap-1">
                  Loại
                  <ArrowUpDown className="size-3 text-muted-foreground" />
                </span>
              </TableHead>
              <TableHead className="w-20 text-right">SL</TableHead>
              <TableHead className="w-28 text-right">Giá</TableHead>
              <TableHead className="w-24 text-right">Phí</TableHead>
              <TableHead className="w-32 text-right">Lãi/Lỗ gộp</TableHead>
              <TableHead
                className="w-32 text-right cursor-pointer select-none"
                aria-sort={getAriaSortValue("net_pnl", sort, order)}
                onClick={() => handleSort("net_pnl")}
              >
                <span className="inline-flex items-center gap-1 justify-end">
                  Lãi/Lỗ ròng
                  <ArrowUpDown className="size-3 text-muted-foreground" />
                </span>
              </TableHead>
              <TableHead className="w-10 text-center">AI</TableHead>
              <TableHead className="w-10 text-center" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade) => (
              <TableRow key={trade.id}>
                <TableCell className="text-sm">
                  {formatDateVN(trade.trade_date)}
                </TableCell>
                <TableCell className="font-mono text-sm font-bold">
                  {trade.ticker_symbol}
                </TableCell>
                <TableCell className="text-center">
                  {trade.side === "BUY" ? (
                    <Badge className="text-[#26a69a] bg-[#26a69a]/10 border-transparent">
                      MUA
                    </Badge>
                  ) : (
                    <Badge className="text-[#ef5350] bg-[#ef5350]/10 border-transparent">
                      BÁN
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-bold">
                  {trade.quantity}
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-bold">
                  {formatVND(trade.price)}
                </TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">
                  {formatVND(trade.total_fee)}
                </TableCell>
                <TableCell className="text-right">
                  {renderPnl(trade.gross_pnl, trade.side)}
                </TableCell>
                <TableCell className="text-right">
                  {renderPnl(trade.net_pnl, trade.side)}
                </TableCell>
                <TableCell className="text-center">
                  {trade.daily_pick_id !== null && (
                    <span title="Theo gợi ý AI">
                      <Sparkles className="size-4 text-blue-600 dark:text-blue-400 inline-block" />
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-center">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => onDelete(trade)}
                  >
                    <Trash2 className="size-4 text-muted-foreground hover:text-destructive" />
                    <span className="sr-only">Xóa</span>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-4 py-3 border-t">
        <p className="text-sm text-muted-foreground">
          Hiển thị {start}-{end} / {total} giao dịch
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            Trước
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            Sau
          </Button>
        </div>
      </div>
    </Card>
  );
}
