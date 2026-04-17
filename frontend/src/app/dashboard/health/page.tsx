"use client";

import { Activity } from "lucide-react";
import { HealthStatusCards } from "@/components/health-status-cards";
import { DataFreshnessTable } from "@/components/data-freshness-table";
import { ErrorRateChart } from "@/components/error-rate-chart";
import { DbPoolStatus } from "@/components/db-pool-status";
import { JobTriggerButtons } from "@/components/job-trigger-buttons";

export default function HealthPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Activity className="size-6" />
            Sức khỏe hệ thống
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Theo dõi trạng thái job, độ tươi dữ liệu, lỗi và kết nối database
          </p>
        </div>
      </div>

      <HealthStatusCards />

      <div className="grid gap-8 lg:grid-cols-2">
        <DataFreshnessTable />
        <div className="space-y-8">
          <DbPoolStatus />
          <JobTriggerButtons />
        </div>
      </div>

      <ErrorRateChart />
    </div>
  );
}
