"use client";

import { LineChart } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PTOverviewTab } from "@/components/paper-trading/pt-overview-tab";
import { PTTradesTable } from "@/components/paper-trading/pt-trades-table";
import { PTSettingsForm } from "@/components/paper-trading/pt-settings-form";

export default function PaperTradingPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <LineChart className="size-6" />
          Paper Trading
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Giả lập và theo dõi hiệu quả tín hiệu AI
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Tổng quan</TabsTrigger>
          <TabsTrigger value="trades">Lệnh</TabsTrigger>
          <TabsTrigger value="analytics" disabled>Phân tích</TabsTrigger>
          <TabsTrigger value="calendar" disabled>Lịch</TabsTrigger>
          <TabsTrigger value="settings">Cài đặt</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <PTOverviewTab />
        </TabsContent>

        <TabsContent value="trades">
          <PTTradesTable />
        </TabsContent>

        <TabsContent value="analytics">
          <div className="py-8 text-center text-muted-foreground text-sm">
            Sắp có — Phase 26
          </div>
        </TabsContent>

        <TabsContent value="calendar">
          <div className="py-8 text-center text-muted-foreground text-sm">
            Sắp có — Phase 26
          </div>
        </TabsContent>

        <TabsContent value="settings">
          <PTSettingsForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}
