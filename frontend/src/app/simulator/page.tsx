"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
import { PendingSignals } from "@/components/simulator/pending-signals";
import { EquityChart } from "@/components/simulator/equity-chart";
import { PnlTimeline } from "@/components/simulator/pnl-timeline";
import { PortfolioReviewPanel } from "@/components/simulator/portfolio-review-panel";
import { ComparisonSection } from "@/components/simulator/comparison-section";

export default function SimulatorPage() {
  const [activePortfolio, setActivePortfolio] = useState<"ai" | "user" | "compare">("ai");
  const portfolioType = activePortfolio === "compare" ? "ai" : activePortfolio;
  const { data: portfolio, isLoading } = useSimulatorPortfolio(portfolioType);
  const resetMutation = useResetSimulator();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  function handleReset() {
    resetMutation.mutate(activePortfolio, {
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

      {/* Top-level portfolio tabs */}
      <Tabs value={activePortfolio} onValueChange={(v) => setActivePortfolio(v as "ai" | "user" | "compare")}>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <TabsList>
            <TabsTrigger value="ai">🤖 AI Portfolio</TabsTrigger>
            <TabsTrigger value="user">👤 Danh mục thủ công</TabsTrigger>
            <TabsTrigger value="compare">📊 So sánh</TabsTrigger>
          </TabsList>

          {/* Reset button — resets active portfolio (hidden on compare tab) */}
          {activePortfolio !== "compare" && (
          <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
            <DialogTrigger
              render={<Button variant="destructive" size="sm" />}
            >
              Reset {activePortfolio === "ai" ? "danh mục AI" : "danh mục User"}
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Xác nhận reset</DialogTitle>
                <DialogDescription>
                  Reset {activePortfolio === "ai" ? "danh mục AI" : "danh mục User"}.
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
          )}
        </div>

        {/* Shared portfolio content — driven by activePortfolio */}
        <div className="mt-6 space-y-6">
          {activePortfolio === "compare" ? (
            <ComparisonSection />
          ) : (
            <>
              {/* Portfolio Summary + Positions */}
              {isLoading ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-24 rounded-xl" />
                    ))}
                  </div>
                  <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                </div>
              ) : portfolio ? (
                <>
                  <PortfolioSummary data={portfolio} />
                  <PositionsTable positions={portfolio.positions} />
                  <PortfolioReviewPanel portfolioType={activePortfolio} />
                </>
              ) : null}

              {/* Sub-tabs — different per portfolio type */}
              {activePortfolio === "ai" ? (
                <Tabs defaultValue={0}>
                  <div className="w-full overflow-x-auto">
                    <TabsList>
                      <TabsTrigger value={0} className="flex-shrink-0">Tín hiệu AI</TabsTrigger>
                      <TabsTrigger value={1} className="flex-shrink-0">Lịch sử</TabsTrigger>
                      <TabsTrigger value={2} className="flex-shrink-0">Hiệu suất</TabsTrigger>
                      <TabsTrigger value={3} className="flex-shrink-0">Độ chính xác AI</TabsTrigger>
                    </TabsList>
                  </div>
                  <TabsContent value={0} className="pt-4">
                    <PendingSignals />
                  </TabsContent>
                  <TabsContent value={1} className="pt-4">
                    <TradeHistory portfolioType="ai" />
                  </TabsContent>
                  <TabsContent value={2} className="pt-4">
                    <div className="space-y-6">
                      <EquityChart portfolioType="ai" />
                      <PnlTimeline portfolioType="ai" />
                    </div>
                  </TabsContent>
                  <TabsContent value={3} className="pt-4">
                    <AiAccuracyPanel portfolioType="ai" />
                  </TabsContent>
                </Tabs>
              ) : (
                <Tabs defaultValue={0}>
                  <div className="w-full overflow-x-auto">
                    <TabsList>
                      <TabsTrigger value={0} className="flex-shrink-0">Giao dịch mới</TabsTrigger>
                      <TabsTrigger value={1} className="flex-shrink-0">Lịch sử</TabsTrigger>
                      <TabsTrigger value={2} className="flex-shrink-0">Hiệu suất</TabsTrigger>
                      <TabsTrigger value={3} className="flex-shrink-0">Độ chính xác</TabsTrigger>
                    </TabsList>
                  </div>
                  <TabsContent value={0} className="pt-4">
                    <TradeForm />
                  </TabsContent>
                  <TabsContent value={1} className="pt-4">
                    <TradeHistory portfolioType="user" />
                  </TabsContent>
                  <TabsContent value={2} className="pt-4">
                    <div className="space-y-6">
                      <EquityChart portfolioType="user" />
                      <PnlTimeline portfolioType="user" />
                    </div>
                  </TabsContent>
                  <TabsContent value={3} className="pt-4">
                    <AiAccuracyPanel portfolioType="user" />
                  </TabsContent>
                </Tabs>
              )}
            </>
          )}
        </div>
      </Tabs>
    </div>
  );
}
