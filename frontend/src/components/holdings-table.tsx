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
import { useHoldings } from "@/lib/hooks";
import type { HoldingResponse } from "@/lib/api";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

export function HoldingsTable() {
  const { data: holdings, isLoading } = useHoldings();
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo<ColumnDef<HoldingResponse>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: "Mã CK",
        cell: ({ row }) => (
          <span className="font-mono font-bold">{row.original.symbol}</span>
        ),
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
        cell: ({ row }) => (
          <span className="font-mono">
            {row.original.market_price != null
              ? formatVND(row.original.market_price)
              : "—"}
          </span>
        ),
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
    [],
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
