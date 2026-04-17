"use client";

import { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useAllocationData } from "@/lib/hooks";

const COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#f43f5e",
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
  "#9ca3af",
];

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

function formatCompactVND(value: number): string {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

interface SliceData {
  name: string;
  value: number;
  percentage: number;
}

function groupSlices(data: SliceData[]): SliceData[] {
  if (data.length <= 7) return data;
  const top = data.slice(0, 7);
  const rest = data.slice(7);
  const otherValue = rest.reduce((sum, d) => sum + d.value, 0);
  const otherPct = rest.reduce((sum, d) => sum + d.percentage, 0);
  return [
    ...top,
    { name: "Khác", value: otherValue, percentage: Math.round(otherPct * 100) / 100 },
  ];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: SliceData; name: string }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  const idx = 0; // Color from the cell
  const sliceName = item.name;

  return (
    <div
      className="rounded-md border shadow-md"
      style={{
        background: "var(--popover)",
        borderColor: "var(--border)",
        padding: "8px 12px",
      }}
    >
      <p className="text-sm font-semibold">{sliceName}</p>
      <p className="text-xs font-mono text-muted-foreground">
        {formatVND(item.value)} ₫ ({item.percentage.toFixed(1)}%)
      </p>
    </div>
  );
}

export function AllocationChart() {
  const [mode, setMode] = useState<"ticker" | "sector">("ticker");
  const { data, isLoading } = useAllocationData(mode);

  const slices = data?.data ? groupSlices(data.data) : [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg font-semibold">
            Phân bổ danh mục
          </CardTitle>
          <Tabs
            value={mode}
            onValueChange={(v) => setMode(v as "ticker" | "sector")}
            className="ml-auto"
          >
            <TabsList className="h-7">
              <TabsTrigger value="ticker" className="text-xs px-2">
                Mã CK
              </TabsTrigger>
              <TabsTrigger value="sector" className="text-xs px-2">
                Ngành
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-80 w-full rounded-lg" />
        ) : !slices.length ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu phân bổ. Thêm giao dịch mua để bắt đầu.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            {/* Pie chart with center label */}
            <div className="relative w-full" style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {slices.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              {/* Center label */}
              <div className="absolute inset-0 flex items-center justify-center flex-col pointer-events-none">
                <span className="text-lg font-semibold font-mono">
                  {data?.total_value ? formatCompactVND(data.total_value) : "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  Tổng giá trị
                </span>
              </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 mt-2">
              {slices.map((item, index) => (
                <div key={item.name} className="flex items-center gap-1">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-xs text-muted-foreground">
                    {item.name} ({item.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
