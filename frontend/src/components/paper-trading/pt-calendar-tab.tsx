"use client";

import { PTCalendarHeatmap } from "./pt-calendar-heatmap";
import { PTPeriodicTable } from "./pt-periodic-table";

export function PTCalendarTab() {
  return (
    <div className="space-y-6 mt-4">
      <PTCalendarHeatmap />
      <PTPeriodicTable />
    </div>
  );
}
