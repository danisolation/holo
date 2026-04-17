"use client";

import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CSVPreviewRow } from "@/lib/api";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

interface CSVPreviewTableProps {
  rows: CSVPreviewRow[];
}

function StatusIcon({ status }: { status: CSVPreviewRow["status"] }) {
  switch (status) {
    case "valid":
      return <CheckCircle className="size-4 text-[#26a69a]" />;
    case "warning":
      return <AlertTriangle className="size-4 text-[#f59e0b]" />;
    case "error":
      return <XCircle className="size-4 text-[#ef5350]" />;
  }
}

function rowClassName(status: CSVPreviewRow["status"]): string {
  switch (status) {
    case "warning":
      return "bg-[#f59e0b]/10 border-l-2 border-[#f59e0b]";
    case "error":
      return "bg-[#ef5350]/10 border-l-2 border-[#ef5350]";
    default:
      return "";
  }
}

export function CSVPreviewTable({ rows }: CSVPreviewTableProps) {
  return (
    <div className="max-h-[360px] overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead className="w-12">Row</TableHead>
            <TableHead className="w-20">Mã CK</TableHead>
            <TableHead className="w-16">Loại</TableHead>
            <TableHead className="w-20">SL</TableHead>
            <TableHead className="w-24">Giá</TableHead>
            <TableHead className="w-24">Ngày GD</TableHead>
            <TableHead className="w-20">Phí</TableHead>
            <TableHead>Vấn đề</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.row_number} className={rowClassName(row.status)}>
              <TableCell>
                <StatusIcon status={row.status} />
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {row.row_number}
              </TableCell>
              <TableCell className="font-mono font-semibold">
                {row.symbol}
              </TableCell>
              <TableCell>
                <Badge
                  variant="secondary"
                  className={
                    row.side === "BUY"
                      ? "text-[#26a69a] bg-[#26a69a]/10"
                      : "text-[#ef5350] bg-[#ef5350]/10"
                  }
                >
                  {row.side === "BUY" ? "Mua" : "Bán"}
                </Badge>
              </TableCell>
              <TableCell className="font-mono">
                {row.quantity.toLocaleString()}
              </TableCell>
              <TableCell className="font-mono">
                {formatVND(row.price)}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {row.trade_date}
              </TableCell>
              <TableCell className="font-mono text-muted-foreground">
                {row.fees > 0 ? formatVND(row.fees) : "—"}
              </TableCell>
              <TableCell>
                {row.message && (
                  <span
                    className={`text-xs ${
                      row.status === "error"
                        ? "text-[#ef5350]"
                        : "text-[#f59e0b]"
                    }`}
                  >
                    {row.message}
                  </span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
