"use client";

import { FlaskConical } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { BTConfigTab } from "@/components/backtest/bt-config-tab";
import { BTResultsTab } from "@/components/backtest/bt-results-tab";
import { BTTradesTab } from "@/components/backtest/bt-trades-tab";
import { BTAnalyticsTab } from "@/components/backtest/bt-analytics-tab";

export default function BacktestPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <FlaskConical className="size-6" />
          Backtest AI
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Kiểm tra hiệu quả chiến lược AI trên dữ liệu lịch sử
        </p>
      </div>

      <Tabs data-testid="bt-tabs" defaultValue="config">
        <TabsList>
          <TabsTrigger data-testid="bt-tab-config" value="config">Cấu hình</TabsTrigger>
          <TabsTrigger data-testid="bt-tab-results" value="results">Kết quả</TabsTrigger>
          <TabsTrigger data-testid="bt-tab-trades" value="trades">Lệnh</TabsTrigger>
          <TabsTrigger data-testid="bt-tab-analytics" value="analytics">Phân tích</TabsTrigger>
        </TabsList>

        <TabsContent value="config">
          <BTConfigTab />
        </TabsContent>
        <TabsContent value="results">
          <BTResultsTab />
        </TabsContent>
        <TabsContent value="trades">
          <BTTradesTab />
        </TabsContent>
        <TabsContent value="analytics">
          <BTAnalyticsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
