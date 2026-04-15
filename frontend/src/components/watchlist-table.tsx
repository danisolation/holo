"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useMarketOverview, useAnalysisSummary } from "@/lib/hooks";
import { useWatchlistStore } from "@/lib/store";
import type { MarketTicker } from "@/lib/api";

/** Signal badge cell — fetches analysis for individual ticker */
function SignalCell({ symbol }: { symbol: string }) {
  const { data, isLoading } = useAnalysisSummary(symbol);

  if (isLoading) return <Skeleton className="h-5 w-16" />;

  const signal = data?.combined?.signal;
  if (!signal)
    return <span className="text-xs text-muted-foreground">—</span>;

  const key = signal.toLowerCase().replace(/\s+/g, "_");
  const isBuy = ["buy", "strong_buy", "bullish"].includes(key);
  const isSell = ["sell", "strong_sell", "bearish"].includes(key);

  return (
    <Badge
      variant="secondary"
      className={
        isBuy
          ? "text-[#26a69a] bg-[#26a69a]/10 gap-1"
          : isSell
            ? "text-[#ef5350] bg-[#ef5350]/10 gap-1"
            : "gap-1"
      }
    >
      {isBuy ? (
        <TrendingUp className="size-3" />
      ) : isSell ? (
        <TrendingDown className="size-3" />
      ) : (
        <Minus className="size-3" />
      )}
      {signal.toUpperCase().replace(/_/g, " ")}
    </Badge>
  );
}

export function WatchlistTable() {
  const router = useRouter();
  const { watchlist, removeFromWatchlist } = useWatchlistStore();
  const { data: marketData, isLoading } = useMarketOverview();
  const [sorting, setSorting] = useState<SortingState>([]);

  // Filter market data to only watchlist symbols
  const rows = useMemo(() => {
    if (!marketData) return [];
    const marketMap = new Map(marketData.map((t) => [t.symbol, t]));
    return watchlist
      .map((symbol) => marketMap.get(symbol))
      .filter((t): t is MarketTicker => t != null);
  }, [marketData, watchlist]);

  const columns = useMemo<ColumnDef<MarketTicker>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="gap-1 -ml-2"
          >
            Mã
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="font-mono font-bold text-sm">
            {row.getValue("symbol")}
          </span>
        ),
      },
      {
        accessorKey: "name",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="gap-1 -ml-2"
          >
            Tên
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="text-sm truncate max-w-[200px] block">
            {row.getValue("name")}
          </span>
        ),
      },
      {
        accessorKey: "last_price",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="gap-1 -ml-2"
          >
            Giá
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const price = row.getValue("last_price") as number | null;
          return (
            <span className="font-mono text-sm">
              {price != null ? price.toLocaleString("vi-VN") : "—"}
            </span>
          );
        },
      },
      {
        accessorKey: "change_pct",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="gap-1 -ml-2"
          >
            Thay đổi
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const pct = row.getValue("change_pct") as number | null;
          if (pct == null)
            return <span className="text-muted-foreground">—</span>;
          const color =
            pct > 0
              ? "text-[#26a69a]"
              : pct < 0
                ? "text-[#ef5350]"
                : "text-muted-foreground";
          return (
            <span className={`font-mono text-sm ${color}`}>
              {pct >= 0 ? "+" : ""}
              {pct.toFixed(2)}%
            </span>
          );
        },
      },
      {
        id: "signal",
        header: "Tín hiệu",
        cell: ({ row }) => <SignalCell symbol={row.original.symbol} />,
        enableSorting: false,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={(e) => {
              e.stopPropagation();
              removeFromWatchlist(row.original.symbol);
            }}
            className="text-muted-foreground hover:text-destructive"
          >
            <X className="size-3.5" />
          </Button>
        ),
        enableSorting: false,
      },
    ],
    [removeFromWatchlist],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  if (watchlist.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-muted-foreground">
          Chưa có mã nào trong danh mục.
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Duyệt tổng quan thị trường để thêm.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: Math.min(watchlist.length, 5) }).map((_, i) => (
          <Skeleton key={i} className="h-12 rounded-md" />
        ))}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={columns.length} className="h-24 text-center">
              Không tìm thấy dữ liệu thị trường cho các mã đang theo dõi.
            </TableCell>
          </TableRow>
        ) : (
          table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              className="cursor-pointer"
              onClick={() => router.push(`/ticker/${row.original.symbol}`)}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
