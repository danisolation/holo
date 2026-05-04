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
import { PriceFlashCell } from "@/components/price-flash-cell";
import { SectorCombobox } from "@/components/sector-combobox";
import { useMarketOverview, useWatchlist, useRemoveFromWatchlist, useSectors, useUpdateSectorGroup } from "@/lib/hooks";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import type { MarketTicker } from "@/lib/api";

export function WatchlistTable() {
  const router = useRouter();
  const { data: watchlistData, isLoading: watchlistLoading } = useWatchlist();
  const removeMutation = useRemoveFromWatchlist();
  const { data: marketData, isLoading: marketLoading } = useMarketOverview();
  const [sorting, setSorting] = useState<SortingState>([]);
  const watchlistSymbols = useMemo(() => watchlistData?.map((w) => w.symbol) ?? [], [watchlistData]);
  const { prices: realtimePrices } = useRealtimePrices(watchlistSymbols);
  const { data: sectorsData } = useSectors();
  const updateSectorMutation = useUpdateSectorGroup();

  // Filter market data to only watchlist symbols
  const rows = useMemo(() => {
    if (!marketData || !watchlistData) return [];
    const marketMap = new Map(marketData.map((t) => [t.symbol, t]));
    return watchlistData
      .map((w) => marketMap.get(w.symbol))
      .filter((t): t is MarketTicker => t != null);
  }, [marketData, watchlistData]);

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
        id: "sector_group",
        header: "Ngành",
        cell: ({ row }) => {
          const watchItem = watchlistData?.find((w) => w.symbol === row.original.symbol);
          return (
            <SectorCombobox
              value={watchItem?.sector_group ?? null}
              onChange={(sector) =>
                updateSectorMutation.mutate({
                  symbol: row.original.symbol,
                  sectorGroup: sector,
                })
              }
              sectors={sectorsData ?? []}
            />
          );
        },
        enableSorting: false,
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
          const symbol = row.original.symbol;
          const rtPrice = realtimePrices[symbol];
          const price = rtPrice?.price ?? (row.getValue("last_price") as number | null);
          const prevPrice = rtPrice ? (row.getValue("last_price") as number | null) : null;
          if (price == null) {
            return <span className="font-mono text-sm">—</span>;
          }
          return (
            <PriceFlashCell value={price} previousValue={prevPrice ?? undefined}>
              <span className="font-mono text-sm">
                {price.toLocaleString("vi-VN")}
              </span>
            </PriceFlashCell>
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
          const symbol = row.original.symbol;
          const rtPrice = realtimePrices[symbol];
          const pct = rtPrice?.change_pct ?? (row.getValue("change_pct") as number | null);
          if (pct == null)
            return <span className="text-muted-foreground">—</span>;
          const color =
            pct > 0
              ? "text-[#26a69a]"
              : pct < 0
                ? "text-[#ef5350]"
                : "text-muted-foreground";
          return (
            <PriceFlashCell value={pct} previousValue={rtPrice ? (row.getValue("change_pct") as number | null) ?? undefined : undefined}>
              <span className={`font-mono text-sm ${color}`}>
                {pct >= 0 ? "+" : ""}
                {pct.toFixed(2)}%
              </span>
            </PriceFlashCell>
          );
        },
      },
      {
        id: "signal",
        header: "Tín hiệu",
        cell: ({ row }) => {
          const watchItem = watchlistData?.find((w) => w.symbol === row.original.symbol);
          const signal = watchItem?.ai_signal;
          const score = watchItem?.ai_score;

          if (!signal)
            return <span className="text-xs text-muted-foreground">—</span>;

          const key = signal.toLowerCase().replace(/\s+/g, "_");
          const isBuy = ["buy", "strong_buy", "bullish", "mua", "strong", "good", "very_positive", "positive"].includes(key);
          const isSell = ["sell", "strong_sell", "bearish", "ban", "weak", "critical", "very_negative", "negative"].includes(key);

          return (
            <div className="flex items-center gap-1.5">
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
              {score != null && (
                <span className="font-mono text-xs text-muted-foreground">{score}/10</span>
              )}
            </div>
          );
        },
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
              removeMutation.mutate(row.original.symbol);
            }}
            className="text-muted-foreground hover:text-destructive"
          >
            <X className="size-3.5" />
          </Button>
        ),
        enableSorting: false,
      },
    ],
    [watchlistData, removeMutation, realtimePrices, sectorsData, updateSectorMutation],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  if (watchlistLoading || marketLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 rounded-md" />
        ))}
      </div>
    );
  }

  if (!watchlistData || watchlistData.length === 0) {
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
