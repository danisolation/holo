"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatVND } from "@/lib/format";
import type { SimulatorPositionResponse } from "@/lib/api";

interface PositionsTableProps {
  positions: SimulatorPositionResponse[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        Chưa có vị thế nào
      </p>
    );
  }

  return (
    <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
    <Table className="min-w-[650px]">
      <TableHeader>
        <TableRow>
          <TableHead>Mã CK</TableHead>
          <TableHead>Tên</TableHead>
          <TableHead className="text-right">SL</TableHead>
          <TableHead className="text-right">Giá TB</TableHead>
          <TableHead className="text-right">Giá hiện tại</TableHead>
          <TableHead className="text-right">Giá trị</TableHead>
          <TableHead className="text-right">Lãi/Lỗ</TableHead>
          <TableHead className="text-right">%</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((p) => {
          const pnlColor =
            p.unrealized_pnl !== null
              ? p.unrealized_pnl >= 0
                ? "var(--trading-bull)"
                : "var(--trading-bear)"
              : undefined;
          return (
            <TableRow key={p.ticker_symbol}>
              <TableCell className="font-medium">{p.ticker_symbol}</TableCell>
              <TableCell>{p.ticker_name}</TableCell>
              <TableCell className="text-right">
                {p.quantity.toLocaleString("vi-VN")}
              </TableCell>
              <TableCell className="text-right">
                {formatVND(p.avg_price)}
              </TableCell>
              <TableCell className="text-right">
                {p.current_price !== null ? formatVND(p.current_price) : "—"}
              </TableCell>
              <TableCell className="text-right">
                {p.market_value !== null ? formatVND(p.market_value) : "—"}
              </TableCell>
              <TableCell className="text-right" style={{ color: pnlColor }}>
                {p.unrealized_pnl !== null
                  ? `${p.unrealized_pnl >= 0 ? "+" : ""}${formatVND(p.unrealized_pnl)}`
                  : "—"}
              </TableCell>
              <TableCell className="text-right" style={{ color: pnlColor }}>
                {p.unrealized_pnl_pct !== null
                  ? `${p.unrealized_pnl_pct >= 0 ? "+" : ""}${p.unrealized_pnl_pct.toFixed(2)}%`
                  : "—"}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
    </div>
  );
}
