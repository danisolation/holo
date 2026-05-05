"use client";

import { useState } from "react";
import { Calendar, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useDailyPicks, useProfile, useTrades, useDeleteTrade } from "@/lib/hooks";
import { formatVND } from "@/lib/format";
import type { DailyPickResponse, TradeResponse } from "@/lib/api";
import { PickCard, PickCardSkeleton } from "@/components/pick-card";
import { AlmostSelectedList } from "@/components/almost-selected-list";
import { ProfileSettingsCard } from "@/components/profile-settings-card";
import { PickPerformanceCards } from "@/components/pick-performance-cards";
import { PickHistoryTable } from "@/components/pick-history-table";
import { TradesTable } from "@/components/trades-table";
import { DeleteTradeDialog } from "@/components/delete-trade-dialog";
import { TradeEntryDialog } from "@/components/trade-entry-dialog";
import type { TradePrefill } from "@/components/trade-entry-dialog";
import { PostTradeCard } from "@/components/post-trade-card";
import { RiskSuggestionBanner } from "@/components/risk-suggestion-banner";
import { HabitDetectionCard } from "@/components/habit-detection-card";
import { ViewingStatsCard } from "@/components/viewing-stats-card";
import { SectorPreferencesCard } from "@/components/sector-preferences-card";
import { MonthlyGoalCard } from "@/components/monthly-goal-card";
import { WeeklyPromptCard } from "@/components/weekly-prompt-card";
import { WeeklyReviewCard } from "@/components/weekly-review-card";
import { AccuracyCard } from "@/components/accuracy-card";

export default function CoachPage() {
  const { data: picksData, isLoading, isError, refetch } = useDailyPicks();
  const { data: profile } = useProfile();

  // Tab state
  const [activeTab, setActiveTab] = useState("picks");

  // Trade dialog state (from pick card)
  const [tradeDialogOpen, setTradeDialogOpen] = useState(false);
  const [tradePrefill, setTradePrefill] = useState<TradePrefill | undefined>(undefined);

  // Post-trade state (after successful recording)
  const [lastTradeData, setLastTradeData] = useState<{
    trade: TradeResponse;
    pick: DailyPickResponse;
  } | null>(null);

  // Open trades state
  const [openTradesPage, setOpenTradesPage] = useState(1);
  const [openTradesSort, setOpenTradesSort] = useState("trade_date");
  const [openTradesOrder, setOpenTradesOrder] = useState("desc");
  const [deleteTarget, setDeleteTarget] = useState<TradeResponse | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const { data: tradesData, isLoading: tradesLoading, isError: tradesError } = useTrades({
    side: "BUY",
    page: openTradesPage,
    sort: openTradesSort,
    order: openTradesOrder,
  });
  const deleteMutation = useDeleteTrade();

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

  function handleRecordTrade(pick: DailyPickResponse) {
    setTradePrefill({
      ticker_symbol: pick.ticker_symbol,
      ticker_name: pick.ticker_name,
      price: pick.entry_price ?? 0,
      quantity: pick.position_size_shares ?? 100,
      daily_pick_id: pick.id,
      stop_loss: pick.stop_loss,
      take_profit_1: pick.take_profit_1,
    });
    setTradeDialogOpen(true);
  }

  function handleTradeCreated(trade: TradeResponse) {
    // Find the pick that was used (from prefill data)
    const matchedPick = picksData?.picks.find(
      (p) => p.id === tradePrefill?.daily_pick_id
    ) ?? picksData?.almost_selected?.find(
      (p) => p.id === tradePrefill?.daily_pick_id
    );

    if (matchedPick) {
      setLastTradeData({ trade, pick: matchedPick });
    }

    setTradePrefill(undefined);
  }

  function handleDismissPostTrade() {
    setLastTradeData(null);
  }

  function handleViewJournal() {
    setLastTradeData(null);
    setActiveTab("journal");
  }

  const showOpenTrades =
    !tradesLoading && !tradesError && tradesData && tradesData.trades.length > 0;

  return (
    <div className="space-y-6">
      {/* Risk Suggestion Banner (global, outside tabs) */}
      <RiskSuggestionBanner />

      {/* Page header (global, outside tabs) */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gợi ý hôm nay</h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI chọn {picksData?.picks.length ?? 0} mã phù hợp với vốn{" "}
            {formatVND(profile?.capital ?? 50_000_000)}đ
          </p>
        </div>
        <ProfileSettingsCard />
      </div>

      {/* Tab navigation */}
      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as string)}>
        <TabsList>
          <TabsTrigger value="picks">Picks</TabsTrigger>
          <TabsTrigger value="journal">Nhật ký</TabsTrigger>
          <TabsTrigger value="goals">Mục tiêu</TabsTrigger>
        </TabsList>

        {/* === TAB: Picks === */}
        <TabsContent value="picks">
          <div className="space-y-6 pt-2">
            {/* Post-trade success card (conditional) */}
            {lastTradeData && (
              <PostTradeCard
                tickerSymbol={lastTradeData.trade.ticker_symbol}
                tickerName={lastTradeData.trade.ticker_name}
                quantity={lastTradeData.trade.quantity}
                price={lastTradeData.trade.price}
                stopLoss={lastTradeData.pick.stop_loss}
                takeProfit1={lastTradeData.pick.take_profit_1}
                takeProfit2={lastTradeData.pick.take_profit_2}
                onDismiss={handleDismissPostTrade}
                onViewJournal={handleViewJournal}
              />
            )}

            {/* Performance cards */}
            <PickPerformanceCards />

            {/* Today's picks */}
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <PickCardSkeleton key={i} />
                ))}
              </div>
            ) : isError ? (
              <Card className="max-w-md mx-auto">
                <CardContent className="flex flex-col items-center text-center py-12">
                  <AlertTriangle className="size-12 text-destructive/60 mb-4" />
                  <h2 className="text-lg font-bold">Không thể tải gợi ý</h2>
                  <p className="text-sm text-muted-foreground mt-2">
                    Đã xảy ra lỗi khi tải dữ liệu. Vui lòng thử lại.
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => refetch()}
                  >
                    Thử lại
                  </Button>
                </CardContent>
              </Card>
            ) : picksData && picksData.picks.length === 0 ? (
              <Card className="max-w-md mx-auto">
                <CardContent className="flex flex-col items-center text-center py-12">
                  <Calendar className="size-12 text-muted-foreground/40 mb-4" />
                  <h2 className="text-lg font-bold">Chưa có gợi ý hôm nay</h2>
                  <p className="text-sm text-muted-foreground mt-2 max-w-md">
                    Gợi ý sẽ được tạo sau khi phân tích AI chạy xong (~17:00 mỗi ngày
                    giao dịch).
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {picksData?.picks.map((pick) => (
                  <PickCard
                    key={pick.ticker_symbol}
                    pick={pick}
                    onRecordTrade={handleRecordTrade}
                  />
                ))}
              </div>
            )}

            {/* Almost selected */}
            {picksData?.almost_selected && picksData.almost_selected.length > 0 && (
              <AlmostSelectedList tickers={picksData.almost_selected} />
            )}

            {/* AI Accuracy Stats (Phase 66) */}
            <AccuracyCard />
          </div>
        </TabsContent>

        {/* === TAB: Nhật ký === */}
        <TabsContent value="journal">
          <div className="space-y-6 pt-2">
            {/* Open trades */}
            {showOpenTrades && (
              <div className="space-y-4">
                <h2 className="text-lg font-bold">
                  Vị thế đang mở{" "}
                  <Badge variant="secondary">{tradesData.total}</Badge>
                </h2>
                <TradesTable
                  trades={tradesData.trades}
                  total={tradesData.total}
                  page={openTradesPage}
                  pageSize={tradesData.page_size}
                  sort={openTradesSort}
                  order={openTradesOrder}
                  onSortChange={(newSort, newOrder) => {
                    setOpenTradesSort(newSort);
                    setOpenTradesOrder(newOrder);
                  }}
                  onPageChange={setOpenTradesPage}
                  onDelete={handleDeleteClick}
                  isLoading={false}
                />
              </div>
            )}

            {/* Pick history */}
            <PickHistoryTable />

            {/* Behavior insights */}
            <div className="space-y-6">
              <h2 className="text-lg font-bold">Phân tích hành vi</h2>
              <HabitDetectionCard />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ViewingStatsCard />
                <SectorPreferencesCard />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* === TAB: Mục tiêu === */}
        <TabsContent value="goals">
          <div className="space-y-6 pt-2">
            <MonthlyGoalCard />
            <WeeklyPromptCard />
            <WeeklyReviewCard />
          </div>
        </TabsContent>
      </Tabs>

      {/* Trade entry dialog (from pick card) */}
      <TradeEntryDialog
        open={tradeDialogOpen}
        onOpenChange={setTradeDialogOpen}
        prefill={tradePrefill}
        onTradeCreated={handleTradeCreated}
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
