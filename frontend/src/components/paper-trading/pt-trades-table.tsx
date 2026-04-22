"use client";

import { useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperTrades, useClosePaperTrade } from "@/lib/hooks";
import type { PaperTradeResponse } from "@/lib/api";
import { formatVND } from "@/lib/format";
import { TRADE_STATUS_CONFIG } from "@/lib/constants";

export function PTTradesTable() {
  const [symbolFilter, setSymbolFilter] = useState("");
  const [directionFilter, setDirectionFilter] = useState<string | undefined>();
  const [sorting, setSorting] = useState<SortingState>([]);

  const { data, isLoading } = usePaperTrades({
    symbol: symbolFilter || undefined,
    direction: directionFilter,
    limit: 100,
  });

  const closeMutation = useClosePaperTrade();

  const columns: ColumnDef<PaperTradeResponse>[] = [
    {
      accessorKey: "signal_date",
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => column.toggleSorting()}
          className="-ml-3"
        >
          Ngày <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.signal_date}</span>
      ),
    },
    {
      accessorKey: "symbol",
      header: "Mã CK",
      cell: ({ row }) => (
        <span className="font-mono font-bold">{row.original.symbol}</span>
      ),
    },
    {
      accessorKey: "direction",
      header: "Hướng",
      cell: ({ row }) => (
        <Badge
          variant="secondary"
          className={
            row.original.direction === "long"
              ? "text-[#26a69a] bg-[#26a69a]/10"
              : "text-[#ef5350] bg-[#ef5350]/10"
          }
        >
          {row.original.direction === "long" ? "LONG" : "BEARISH"}
        </Badge>
      ),
    },
    {
      accessorKey: "entry_price",
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => column.toggleSorting()}
          className="-ml-3"
        >
          Entry <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-mono">{formatVND(row.original.entry_price)}</span>
      ),
    },
    {
      accessorKey: "exit_price",
      header: "Exit",
      cell: ({ row }) => (
        <span className="font-mono">
          {row.original.exit_price != null
            ? formatVND(row.original.exit_price)
            : "—"}
        </span>
      ),
    },
    {
      accessorKey: "realized_pnl",
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => column.toggleSorting()}
          className="-ml-3"
        >
          P&L <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ row }) => {
        const val = row.original.realized_pnl;
        if (val == null) return <span className="font-mono text-muted-foreground">—</span>;
        const color = val > 0 ? "text-[#26a69a]" : val < 0 ? "text-[#ef5350]" : "";
        const sign = val > 0 ? "+" : "";
        return <span className={`font-mono ${color}`}>{sign}{formatVND(val)}</span>;
      },
    },
    {
      accessorKey: "realized_pnl_pct",
      header: "P&L %",
      cell: ({ row }) => {
        const val = row.original.realized_pnl_pct;
        if (val == null) return <span className="font-mono text-muted-foreground">—</span>;
        const color = val > 0 ? "text-[#26a69a]" : val < 0 ? "text-[#ef5350]" : "";
        const sign = val > 0 ? "+" : "";
        return <span className={`font-mono ${color}`}>{sign}{val.toFixed(2)}%</span>;
      },
    },
    {
      accessorKey: "status",
      header: "Trạng thái",
      cell: ({ row }) => {
        const cfg = TRADE_STATUS_CONFIG[row.original.status] ?? {
          label: row.original.status,
          className: "",
        };
        return (
          <Badge variant="secondary" className={cfg.className}>
            {cfg.label}
          </Badge>
        );
      },
    },
    {
      accessorKey: "confidence",
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => column.toggleSorting()}
          className="-ml-3"
        >
          AI <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ row }) => {
        const score = row.original.confidence;
        const color =
          score >= 7 ? "text-[#26a69a]" : score <= 3 ? "text-[#ef5350]" : "";
        return <span className={`font-mono font-bold ${color}`}>{score}</span>;
      },
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const status = row.original.status;
        if (status !== "active" && status !== "partial_tp") return null;
        return (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={closeMutation.isPending}
            onClick={() => closeMutation.mutate(row.original.id)}
          >
            Đóng
          </Button>
        );
      },
      size: 80,
    },
  ];

  const table = useReactTable({
    data: data?.trades ?? [],
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
    <Card data-testid="pt-trades-table">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Danh sách lệnh</CardTitle>
          <div className="flex items-center gap-2">
            <Filter className="size-4 text-muted-foreground" />
            <Input
              placeholder="Lọc mã CK..."
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
              className="h-8 w-24 font-mono text-xs"
            />
            <div className="flex gap-1">
              <Button
                variant={directionFilter === undefined ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setDirectionFilter(undefined)}
              >
                Tất cả
              </Button>
              <Button
                variant={directionFilter === "long" ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setDirectionFilter("long")}
              >
                Long
              </Button>
              <Button
                variant={directionFilter === "bearish" ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setDirectionFilter("bearish")}
              >
                Bearish
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {!data || data.trades.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground text-sm">
            Chưa có lệnh paper trading nào.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((hg) => (
                  <TableRow key={hg.id}>
                    {hg.headers.map((header) => (
                      <TableHead key={header.id}>
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
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
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="px-4 py-2 text-xs text-muted-foreground border-t">
              {data.total} lệnh
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
