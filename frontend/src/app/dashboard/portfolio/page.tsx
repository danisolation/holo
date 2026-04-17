"use client";

import { Briefcase } from "lucide-react";
import { PortfolioSummary } from "@/components/portfolio-summary";
import { HoldingsTable } from "@/components/holdings-table";
import { TradeForm } from "@/components/trade-form";
import { TradeHistory } from "@/components/trade-history";
import { PerformanceChart } from "@/components/performance-chart";
import { AllocationChart } from "@/components/allocation-chart";
import CSVImportDialog from "@/components/csv-import-dialog";

export default function PortfolioPage() {
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Briefcase className="size-6" />
            Danh mục đầu tư
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Theo dõi giao dịch, lời lỗ và vị thế cổ phiếu
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CSVImportDialog />
          <TradeForm />
        </div>
      </div>

      {/* Summary cards */}
      <PortfolioSummary />

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3">
          <PerformanceChart />
        </div>
        <div className="lg:col-span-2">
          <AllocationChart />
        </div>
      </div>

      {/* Holdings table */}
      <HoldingsTable />

      {/* Trade history */}
      <TradeHistory />
    </div>
  );
}
