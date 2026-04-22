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
import { ArrowUpDown, Filter, Pencil, Trash2 } from "lucide-react";
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
import { useTradeHistory } from "@/lib/hooks";
import type { TradeResponse } from "@/lib/api";
import { TradeEditDialog } from "@/components/trade-edit-dialog";
import { TradeDeleteConfirm } from "@/components/trade-delete-confirm";
import { formatVND } from "@/lib/format";

export function TradeHistory() {
  const [tickerFilter, setTickerFilter] = useState("");
  const [sideFilter, setSideFilter] = useState<string | undefined>();
  const [editTrade, setEditTrade] = useState<TradeResponse | null>(null);
  const [deleteTrade, setDeleteTrade] = useState<TradeResponse | null>(null);

  const { data, isLoading } = useTradeHistory({
    ticker: tickerFilter || undefined,
    side: sideFilter,
    limit: 50,
  });

  const [sorting, setSorting] = useState<SortingState>([]);

  const columns: ColumnDef<TradeResponse>[] = [
    {
      accessorKey: "trade_date",
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
        <span className="font-mono text-xs">{row.original.trade_date}</span>
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
      accessorKey: "side",
      header: "Loại",
      cell: ({ row }) => (
        <Badge
          variant="secondary"
          className={
            row.original.side === "BUY"
              ? "text-[#26a69a] bg-[#26a69a]/10"
              : "text-[#ef5350] bg-[#ef5350]/10"
          }
        >
          {row.original.side === "BUY" ? "Mua" : "Bán"}
        </Badge>
      ),
    },
    {
      accessorKey: "quantity",
      header: "SL",
      cell: ({ row }) => (
        <span className="font-mono">{row.original.quantity.toLocaleString()}</span>
      ),
    },
    {
      accessorKey: "price",
      header: ({ column }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => column.toggleSorting()}
          className="-ml-3"
        >
          Giá <ArrowUpDown className="ml-1 size-3" />
        </Button>
      ),
      cell: ({ row }) => (
        <span className="font-mono">{formatVND(row.original.price)}</span>
      ),
    },
    {
      accessorKey: "fees",
      header: "Phí",
      cell: ({ row }) => (
        <span className="font-mono text-muted-foreground">
          {row.original.fees > 0 ? formatVND(row.original.fees) : "—"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setEditTrade(row.original)}
          >
            <Pencil className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={() => setDeleteTrade(row.original)}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      ),
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
    <>
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Lịch sử giao dịch</CardTitle>
          <div className="flex items-center gap-2">
            <Filter className="size-4 text-muted-foreground" />
            <Input
              placeholder="Lọc mã CK..."
              value={tickerFilter}
              onChange={(e) => setTickerFilter(e.target.value.toUpperCase())}
              className="h-8 w-24 font-mono text-xs"
            />
            <div className="flex gap-1">
              <Button
                variant={sideFilter === undefined ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setSideFilter(undefined)}
              >
                Tất cả
              </Button>
              <Button
                variant={sideFilter === "BUY" ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setSideFilter("BUY")}
              >
                Mua
              </Button>
              <Button
                variant={sideFilter === "SELL" ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setSideFilter("SELL")}
              >
                Bán
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {!data || data.trades.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground text-sm">
            Chưa có giao dịch nào.
          </div>
        ) : (
          <>
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
            <div className="px-4 py-2 text-xs text-muted-foreground border-t">
              {data.total} giao dịch
            </div>
          </>
        )}
      </CardContent>
    </Card>
      {editTrade && (
        <TradeEditDialog
          trade={editTrade}
          open={!!editTrade}
          onOpenChange={(open) => { if (!open) setEditTrade(null); }}
        />
      )}
      {deleteTrade && (
        <TradeDeleteConfirm
          trade={deleteTrade}
          open={!!deleteTrade}
          onOpenChange={(open) => { if (!open) setDeleteTrade(null); }}
        />
      )}
    </>
  );
}
