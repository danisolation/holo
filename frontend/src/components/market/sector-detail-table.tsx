"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import type { SectorDetailTickerItem } from "@/lib/api";

interface SectorDetailTableProps {
  tickers: SectorDetailTickerItem[];
}

type SortKey = keyof SectorDetailTickerItem;

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "Mã" },
  { key: "name", label: "Tên" },
  { key: "industry", label: "Ngành con" },
  { key: "close", label: "Giá" },
  { key: "volume", label: "KL" },
  { key: "change_7d", label: "%7D" },
  { key: "change_30d", label: "%30D" },
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

export function SectorDetailTable({ tickers }: SectorDetailTableProps) {
  const [sortBy, setSortBy] = useState<SortKey>("market_cap");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    return [...tickers].sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortOrder === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      const diff = (aVal as number) - (bVal as number);
      return sortOrder === "asc" ? diff : -diff;
    });
  }, [tickers, sortBy, sortOrder]);

  function handleSort(key: SortKey) {
    if (sortBy === key) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder("desc");
    }
  }

  function sortIndicator(col: SortKey) {
    if (sortBy !== col) return null;
    return sortOrder === "asc" ? " ▲" : " ▼";
  }

  if (tickers.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-8">
        Không có cổ phiếu trong ngành này
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {COLUMNS.map((col) => (
            <TableHead
              key={col.key}
              className="cursor-pointer select-none hover:text-primary"
              onClick={() => handleSort(col.key)}
            >
              {col.label}
              {sortIndicator(col.key)}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((ticker) => (
          <TableRow key={ticker.symbol}>
            <TableCell>
              <Link
                href={`/ticker/${ticker.symbol}`}
                className="text-primary hover:underline font-mono"
              >
                {ticker.symbol}
              </Link>
            </TableCell>
            <TableCell className="max-w-[200px] truncate">
              {ticker.name}
            </TableCell>
            <TableCell className="text-xs">
              {ticker.industry ?? "—"}
            </TableCell>
            <TableCell>
              {ticker.close != null ? ticker.close.toLocaleString() : "—"}
            </TableCell>
            <TableCell>
              {ticker.volume != null
                ? ticker.volume.toLocaleString("vi-VN")
                : "—"}
            </TableCell>
            <TableCell>{formatChange(ticker.change_7d)}</TableCell>
            <TableCell>{formatChange(ticker.change_30d)}</TableCell>
            <TableCell>{formatMarketCap(ticker.market_cap)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
