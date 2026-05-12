"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { useSimulatorPortfolio, useResetSimulator } from "@/lib/hooks";
import { PortfolioSummary } from "@/components/simulator/portfolio-summary";
import { PositionsTable } from "@/components/simulator/positions-table";
import { TradeForm } from "@/components/simulator/trade-form";
import { TradeHistory } from "@/components/simulator/trade-history";
import { AiAccuracyPanel } from "@/components/simulator/ai-accuracy-panel";
import { AutoTradeToggle } from "@/components/simulator/auto-trade-toggle";
import { PendingSignals } from "@/components/simulator/pending-signals";

export default function SimulatorPage() {
  const { data: portfolio, isLoading } = useSimulatorPortfolio();
  const resetMutation = useResetSimulator();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  function handleReset() {
    resetMutation.mutate(undefined, {
      onSuccess: () => setResetDialogOpen(false),
    });
  }

  return (
    <div data-testid="simulator-page" className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          Mô phỏng giao dịch
        </h2>
        <p className="text-sm text-muted-foreground">
          Kiểm chứng tín hiệu AI bằng giao dịch giả lập
        </p>
      </div>

      {/* Controls: toggle + reset */}
      <div className="flex items-center justify-between">
        <AutoTradeToggle />
        <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
          <DialogTrigger
            render={<Button variant="destructive" size="sm" />}
          >
            Reset danh mục
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Xác nhận reset</DialogTitle>
              <DialogDescription>
                Tất cả vị thế và lịch sử giao dịch sẽ bị xoá. Vốn sẽ trở về
                mức ban đầu. Hành động này không thể hoàn tác.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>
                Huỷ
              </DialogClose>
              <Button
                variant="destructive"
                onClick={handleReset}
                disabled={resetMutation.isPending}
              >
                {resetMutation.isPending ? "Đang reset..." : "Xác nhận reset"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Portfolio Summary */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground py-6 text-center">
          Đang tải danh mục...
        </p>
      ) : portfolio ? (
        <>
          <PortfolioSummary data={portfolio} />
          <PositionsTable positions={portfolio.positions} />
        </>
      ) : null}

      {/* Tabs: AI Signals | Trade form | History | AI Accuracy */}
      <Tabs defaultValue={0}>
        <TabsList>
          <TabsTrigger value={0}>Tín hiệu AI</TabsTrigger>
          <TabsTrigger value={1}>Giao dịch mới</TabsTrigger>
          <TabsTrigger value={2}>Lịch sử</TabsTrigger>
          <TabsTrigger value={3}>Độ chính xác AI</TabsTrigger>
        </TabsList>
        <TabsContent value={0} className="pt-4">
          <PendingSignals />
        </TabsContent>
        <TabsContent value={1} className="pt-4">
          <TradeForm />
        </TabsContent>
        <TabsContent value={2} className="pt-4">
          <TradeHistory />
        </TabsContent>
        <TabsContent value={3} className="pt-4">
          <AiAccuracyPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
