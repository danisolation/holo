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
import { ArrowUpDown, SearchX, FilterX } from "lucide-react";
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
import { SectorCombobox } from "@/components/sector-combobox";
import {
  useDiscovery,
  useWatchlist,
  useAddToWatchlist,
  useSectors,
} from "@/lib/hooks";
import type { DiscoveryItem } from "@/lib/api";

// --- Score bar cell ---

function ScoreCell({ value }: { value: number | null }) {
  if (value == null)
    return <span className="text-xs text-muted-foreground">—</span>;
  const pct = (value / 10) * 100;
  const color =
    value >= 7
      ? "bg-[#26a69a]"
      : value >= 4
        ? "bg-amber-500"
        : "bg-[#ef5350]";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-full bg-muted rounded-full">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs w-6 text-right">
        {value.toFixed(1)}
      </span>
    </div>
  );
}

// --- Signal type filter options ---

const SIGNAL_OPTIONS = [
  { value: "all", label: "Tất cả tín hiệu" },
  { value: "rsi", label: "RSI" },
  { value: "macd", label: "MACD" },
  { value: "adx", label: "ADX" },
  { value: "volume", label: "Volume" },
  { value: "pe", label: "P/E" },
  { value: "roe", label: "ROE" },
] as const;

// --- Skeleton loading table ---

function SkeletonTable() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-12 rounded-md" />
      ))}
    </div>
  );
}

// --- Empty states ---

function NoDataState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <SearchX className="size-6 text-muted-foreground mb-3" />
      <p className="font-medium">Chưa có dữ liệu khám phá</p>
      <p className="text-sm text-muted-foreground mt-1">
        Hệ thống sẽ tự động quét và chấm điểm cổ phiếu sau phiên giao dịch
        hàng ngày.
      </p>
    </div>
  );
}

function FilterEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <FilterX className="size-6 text-muted-foreground mb-3" />
      <p className="font-medium">Không tìm thấy kết quả</p>
      <p className="text-sm text-muted-foreground mt-1">
        Thử thay đổi bộ lọc ngành hoặc loại tín hiệu.
      </p>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="font-medium">Không thể tải dữ liệu khám phá</p>
      <p className="text-sm text-muted-foreground mt-1">
        Vui lòng thử lại sau hoặc kiểm tra kết nối mạng.
      </p>
    </div>
  );
}

// --- Stale data check ---

function isStaleData(scoreDate: string): boolean {
  const today = new Date();
  const score = new Date(scoreDate);
  // Simple check: if score_date is more than 1 day behind today
  const diffMs = today.getTime() - score.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays > 1.5;
}

// --- Main component ---

export function DiscoveryTable() {
  const router = useRouter();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "total_score", desc: true },
  ]);
  const [sectorFilter, setSectorFilter] = useState<string | null>(null);
  const [signalFilter, setSignalFilter] = useState("all");

  const { data: sectorsData } = useSectors();
  const {
    data: discoveryData,
    isLoading,
    isError,
  } = useDiscovery({
    sector: sectorFilter ?? undefined,
    signal_type: signalFilter === "all" ? undefined : signalFilter,
  });
  const { data: watchlistData } = useWatchlist();
  const addMutation = useAddToWatchlist();

  const watchlistSymbols = useMemo(
    () => new Set(watchlistData?.map((w) => w.symbol) ?? []),
    [watchlistData],
  );

  const columns = useMemo<ColumnDef<DiscoveryItem>[]>(
    () => [
      {
        accessorKey: "symbol",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() =>
              column.toggleSorting(column.getIsSorted() === "asc")
            }
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
        size: 80,
      },
      {
        accessorKey: "name",
        header: "Tên",
        cell: ({ row }) => (
          <span className="text-sm truncate max-w-[200px] block">
            {row.getValue("name")}
          </span>
        ),
        enableSorting: false,
        meta: { className: "hidden md:table-cell" },
      },
      {
        accessorKey: "sector",
        header: "Ngành",
        cell: ({ row }) => {
          const sector = row.getValue("sector") as string | null;
          if (!sector) return <span className="text-xs text-muted-foreground">—</span>;
          return (
            <Badge variant="outline" className="text-xs">
              {sector}
            </Badge>
          );
        },
        enableSorting: false,
        meta: { className: "hidden lg:table-cell" },
      },
      {
        accessorKey: "total_score",
        header: ({ column }) => (
          <Button
            variant="ghost"
            size="xs"
            onClick={() =>
              column.toggleSorting(column.getIsSorted() === "asc")
            }
            className="gap-1 -ml-2"
          >
            Điểm
            <ArrowUpDown className="size-3" />
          </Button>
        ),
        cell: ({ row }) => {
          const score = row.getValue("total_score") as number;
          const color =
            score >= 7
              ? "text-[#26a69a]"
              : score >= 4
                ? "text-amber-500"
                : "text-[#ef5350]";
          return (
            <span className={`font-mono font-bold text-sm ${color}`}>
              {score.toFixed(1)}
            </span>
          );
        },
        size: 60,
      },
      {
        accessorKey: "rsi_score",
        header: "RSI",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("rsi_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden lg:table-cell" },
        size: 100,
      },
      {
        accessorKey: "macd_score",
        header: "MACD",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("macd_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden lg:table-cell" },
        size: 100,
      },
      {
        accessorKey: "adx_score",
        header: "ADX",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("adx_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden xl:table-cell" },
        size: 100,
      },
      {
        accessorKey: "volume_score",
        header: "Volume",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("volume_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden xl:table-cell" },
        size: 100,
      },
      {
        accessorKey: "pe_score",
        header: "P/E",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("pe_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden xl:table-cell" },
        size: 100,
      },
      {
        accessorKey: "roe_score",
        header: "ROE",
        cell: ({ row }) => (
          <ScoreCell value={row.getValue("roe_score")} />
        ),
        enableSorting: false,
        meta: { className: "hidden xl:table-cell" },
        size: 100,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => {
          const symbol = row.original.symbol;
          const inWatchlist = watchlistSymbols.has(symbol);
          return (
            <Button
              variant={inWatchlist ? "secondary" : "default"}
              size="xs"
              disabled={inWatchlist || addMutation.isPending}
              onClick={(e) => {
                e.stopPropagation();
                addMutation.mutate(symbol);
              }}
            >
              {inWatchlist ? "Đã thêm" : "Thêm"}
            </Button>
          );
        },
        enableSorting: false,
        size: 80,
      },
    ],
    [watchlistSymbols, addMutation],
  );

  const table = useReactTable({
    data: discoveryData ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const hasFilters = sectorFilter != null || signalFilter !== "all";
  const showStaleWarning =
    discoveryData &&
    discoveryData.length > 0 &&
    discoveryData[0]?.score_date &&
    isStaleData(discoveryData[0].score_date);

  return (
    <div data-testid="discovery-table">
      {/* Stale data warning */}
      {showStaleWarning && (
        <Badge variant="outline" className="text-amber-600 mb-4">
          Dữ liệu cũ — pipeline chưa chạy hôm nay
        </Badge>
      )}

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <SectorCombobox
          value={sectorFilter}
          onChange={setSectorFilter}
          sectors={sectorsData ?? []}
        />
        <select
          value={signalFilter}
          onChange={(e) => setSignalFilter(e.target.value)}
          className="rounded-md border px-2 py-1 text-xs bg-background"
          data-testid="signal-filter"
        >
          {SIGNAL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading skeleton */}
      {isLoading && <SkeletonTable />}

      {/* Error state */}
      {isError && <ErrorState />}

      {/* Empty states */}
      {!isLoading &&
        !isError &&
        discoveryData &&
        discoveryData.length === 0 &&
        (hasFilters ? <FilterEmptyState /> : <NoDataState />)}

      {/* Table */}
      {!isLoading &&
        !isError &&
        discoveryData &&
        discoveryData.length > 0 && (
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const meta = header.column.columnDef.meta as
                      | { className?: string }
                      | undefined;
                    return (
                      <TableHead
                        key={header.id}
                        className={meta?.className}
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() =>
                    router.push(`/ticker/${row.original.symbol}`)
                  }
                >
                  {row.getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta as
                      | { className?: string }
                      | undefined;
                    return (
                      <TableCell
                        key={cell.id}
                        className={meta?.className}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
    </div>
  );
}
