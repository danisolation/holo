"use client";

import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import type { ScreenerTickerItem } from "@/lib/api";

interface ScreenerTableProps {
  data: ScreenerTickerItem[];
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  onSort: (column: string) => void;
}

const COLUMNS: { key: string; label: string }[] = [
  { key: "symbol", label: "Mã" },
  { key: "name", label: "Tên" },
  { key: "sector", label: "Ngành" },
  { key: "close", label: "Giá" },
  { key: "volume", label: "KL" },
  { key: "change_1d", label: "%1D" },
  { key: "change_7d", label: "%7D" },
  { key: "change_30d", label: "%30D" },
  { key: "pe", label: "P/E" },
  { key: "market_cap", label: "Vốn hóa" },
];

function formatChange(val: number | null) {
  if (val == null) return "—";
  const color = val > 0 ? "var(--trading-bull)" : val < 0 ? "var(--trading-bear)" : undefined;
  return (
    <span style={{ color }}>
      {val > 0 ? "+" : ""}
      {val.toFixed(2)}%
    </span>
  );
}

function formatMarketCap(val: number | null) {
  if (val == null) return "—";
  return (val / 1e9).toFixed(1) + " tỷ";
}

export function ScreenerTable({
  data,
  sortBy,
  sortOrder,
  onSort,
}: ScreenerTableProps) {
  if (data.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-8">
        Không tìm thấy kết quả
      </p>
    );
  }

  function sortIndicator(col: string) {
    if (sortBy !== col) return null;
    return sortOrder === "asc" ? " ▲" : " ▼";
  }

  return (
    <div className="overflow-x-auto">
    <Table className="min-w-[700px]">
      <TableHeader>
        <TableRow>
          {COLUMNS.map((col) => (
            <TableHead
              key={col.key}
              className={`cursor-pointer select-none hover:text-primary${
                ["sector", "change_7d", "change_30d", "pe"].includes(col.key) ? " hidden md:table-cell" : ""
              }`}
              onClick={() => onSort(col.key)}
            >
              {col.label}
              {sortIndicator(col.key)}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow key={item.symbol}>
            <TableCell>
              <Link
                href={`/ticker/${item.symbol}`}
                className="text-primary hover:underline font-medium"
              >
                {item.symbol}
              </Link>
            </TableCell>
            <TableCell className="max-w-[200px] truncate">
              {item.name}
            </TableCell>
            <TableCell className="text-xs hidden md:table-cell">{item.sector ?? "—"}</TableCell>
            <TableCell>
              {item.close != null ? item.close.toLocaleString() : "—"}
            </TableCell>
            <TableCell>
              {item.volume != null ? item.volume.toLocaleString() : "—"}
            </TableCell>
            <TableCell>{formatChange(item.change_1d)}</TableCell>
            <TableCell className="hidden md:table-cell">{formatChange(item.change_7d)}</TableCell>
            <TableCell className="hidden md:table-cell">{formatChange(item.change_30d)}</TableCell>
            <TableCell className="hidden md:table-cell">
              {item.pe != null ? item.pe.toFixed(1) : "—"}
            </TableCell>
            <TableCell>{formatMarketCap(item.market_cap)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
    </div>
  );
}
