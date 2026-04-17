"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useHoldings, useCorporateEvents } from "@/lib/hooks";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import type { HoldingResponse, CorporateEventResponse } from "@/lib/api";
import { DilutionBadge } from "@/components/dilution-badge";
import { PriceFlashCell } from "@/components/price-flash-cell";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

export function HoldingsTable() {
  const { data: holdings, isLoading } = useHoldings();
  const { data: rightsEvents } = useCorporateEvents({ type: "RIGHTS_ISSUE" });
  const [sorting, setSorting] = useState<SortingState>([]);

  // Subscribe to real-time prices for held symbols
  const heldSymbols = useMemo(
    () => (holdings ?? []).map((h) => h.symbol),
    [holdings],
  );
  const { prices: realtimePrices } = useRealtimePrices(heldSymbols);

  // Build a map of symbol → upcoming RIGHTS_ISSUE events
  const dilutionMap = useMemo(() => {
    const map = new Map<string, CorporateEventResponse>();
    if (!rightsEvents) return map;
    const today = new Date().toISOString().split("T")[0];
    for (const event of rightsEvents) {
      const exDate = event.ex_date.split("T")[0];
      if (exDate >= today && event.ratio != null) {
        // Keep only the nearest event per symbol
        const existing = map.get(event.symbol);
        if (!existing || exDate < existing.ex_date.split("T")[0]) {
          map.set(event.symbol, event);
        }
      }
    }
    return map;
  }, [rightsEvents]);

  const columns = useMemo<ColumnDef<HoldingResponse>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: "Mã CK",
        cell: ({ row }) => {
          const event = dilutionMap.get(row.original.symbol);
          const dilutionPct = event?.ratio
            ? (event.ratio / (100 + event.ratio)) * 100
            : null;
          return (
            <div className="flex items-center gap-2">
              <span className="font-mono font-semibold">{row.original.symbol}</span>
              {event && dilutionPct != null && (
                <DilutionBadge
                  dilutionPct={dilutionPct}
                  ratio={event.ratio!}
                  exDate={event.ex_date}
                />
              )}
            </div>
          );
        },
      },
      {
        accessorKey: "name",
        header: "Tên",
        cell: ({ row }) => (
          <span className="text-muted-foreground text-xs truncate max-w-[120px] block">
            {row.original.name}
          </span>
        ),
      },
      {
        accessorKey: "quantity",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => column.toggleSorting()}
            className="-ml-3"
          >
            SL <ArrowUpDown className="ml-1 size-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="font-mono">{row.original.quantity.toLocaleString()}</span>
        ),
      },
      {
        accessorKey: "avg_cost",
        header: "Giá TB",
        cell: ({ row }) => (
          <span className="font-mono">{formatVND(row.original.avg_cost)}</span>
        ),
      },
      {
        accessorKey: "market_price",
        header: "Giá TT",
        cell: ({ row }) => {
          const symbol = row.original.symbol;
          const rtPrice = realtimePrices[symbol];
          const price = rtPrice?.price ?? row.original.market_price;
          if (price == null) {
            return <span className="font-mono">—</span>;
          }
          return (
            <PriceFlashCell value={price} previousValue={row.original.market_price ?? undefined}>
              <span className="font-mono">{formatVND(price)}</span>
            </PriceFlashCell>
          );
        },
      },
      {
        accessorKey: "market_value",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => column.toggleSorting()}
            className="-ml-3"
          >
            Giá trị <ArrowUpDown className="ml-1 size-3" />
          </Button>
        ),
        cell: ({ row }) => (
          <span className="font-mono">
            {row.original.market_value != null
              ? formatVND(row.original.market_value)
              : "—"}
          </span>
        ),
      },
      {
        accessorKey: "unrealized_pnl",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => column.toggleSorting()}
            className="-ml-3"
          >
            Lời/Lỗ <ArrowUpDown className="ml-1 size-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const pnl = row.original.unrealized_pnl;
          const pct = row.original.unrealized_pnl_pct;
          if (pnl == null) return <span className="text-muted-foreground">—</span>;
          const isPositive = pnl >= 0;
          return (
            <div className="flex items-center gap-1">
              {isPositive ? (
                <TrendingUp className="size-3 text-[#26a69a]" />
              ) : (
                <TrendingDown className="size-3 text-[#ef5350]" />
              )}
              <span
                className={`font-mono text-sm ${isPositive ? "text-[#26a69a]" : "text-[#ef5350]"}`}
              >
                {formatVND(pnl)}
                {pct != null && ` (${pct > 0 ? "+" : ""}${pct.toFixed(1)}%)`}
              </span>
            </div>
          );
        },
      },
    ],
    [dilutionMap, realtimePrices],
  );

  const table = useReactTable({
    data: holdings ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-4">
          <Skeleton className="h-48 w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Danh mục đang nắm giữ</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {!holdings || holdings.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground text-sm">
            Chưa có vị thế nào. Thêm giao dịch mua để bắt đầu.
          </div>
        ) : (
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id}>
                  {hg.headers.map((header) => (
                    <TableHead key={header.id}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
