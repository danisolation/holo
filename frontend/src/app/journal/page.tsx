"use client";

import { useState } from "react";
import { Plus, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TradeStatsCards } from "@/components/trade-stats-cards";
import { TradeFilters } from "@/components/trade-filters";
import { TradesTable } from "@/components/trades-table";
import { TradeEntryDialog } from "@/components/trade-entry-dialog";
import { DeleteTradeDialog } from "@/components/delete-trade-dialog";
import { useTrades, useDeleteTrade } from "@/lib/hooks";
import type { TradeResponse } from "@/lib/api";

export default function JournalPage() {
  // Filter state
  const [ticker, setTicker] = useState("");
  const [side, setSide] = useState("");

  // Sort state
  const [sort, setSort] = useState("trade_date");
  const [order, setOrder] = useState("desc");

  // Pagination state
  const [page, setPage] = useState(1);

  // Dialog state
  const [entryDialogOpen, setEntryDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TradeResponse | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Data hooks
  const {
    data: tradesData,
    isLoading,
    isError,
    refetch,
  } = useTrades({
    page,
    ticker: ticker || undefined,
    side: side || undefined,
    sort,
    order,
  });
  const deleteMutation = useDeleteTrade();

  // Reset page to 1 when filters change
  function handleTickerChange(value: string) {
    setTicker(value);
    setPage(1);
  }
  function handleSideChange(value: string) {
    setSide(value);
    setPage(1);
  }

  // Delete flow
  function handleDeleteClick(trade: TradeResponse) {
    setDeleteTarget(trade);
    setDeleteDialogOpen(true);
  }
  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  }

  return (
    <div className="space-y-8">
      {/* Page header: title + CTA button */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">
          Nhật ký giao dịch
        </h1>
        <Button onClick={() => setEntryDialogOpen(true)}>
          <Plus className="size-4 mr-2" />
          Ghi lệnh
        </Button>
      </div>

      {/* Stats cards row */}
      <TradeStatsCards />

      {/* Filter bar */}
      <TradeFilters
        ticker={ticker}
        onTickerChange={handleTickerChange}
        side={side}
        onSideChange={handleSideChange}
      />

      {/* Error state */}
      {isError ? (
        <Card className="py-16 text-center">
          <AlertTriangle className="mx-auto size-12 text-destructive/60" />
          <p className="text-lg font-bold mt-4">Không thể tải nhật ký</p>
          <p className="text-sm text-muted-foreground mt-2">
            Đã xảy ra lỗi khi tải dữ liệu giao dịch. Vui lòng thử lại.
          </p>
          <Button variant="outline" className="mt-4" onClick={() => refetch()}>
            Thử lại
          </Button>
        </Card>
      ) : (
        <TradesTable
          trades={tradesData?.trades ?? []}
          total={tradesData?.total ?? 0}
          page={page}
          pageSize={tradesData?.page_size ?? 20}
          sort={sort}
          order={order}
          onSortChange={(newSort, newOrder) => {
            setSort(newSort);
            setOrder(newOrder);
          }}
          onPageChange={setPage}
          onDelete={handleDeleteClick}
          onCreateFirst={() => setEntryDialogOpen(true)}
          isLoading={isLoading}
        />
      )}

      {/* Trade entry dialog */}
      <TradeEntryDialog
        open={entryDialogOpen}
        onOpenChange={setEntryDialogOpen}
      />

      {/* Delete confirmation dialog */}
      <DeleteTradeDialog
        trade={deleteTarget}
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          setDeleteDialogOpen(open);
          if (!open) setDeleteTarget(null);
        }}
        onConfirm={handleDeleteConfirm}
        isDeleting={deleteMutation.isPending}
      />
    </div>
  );
}
