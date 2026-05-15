"use client";

import { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useComparison } from "@/lib/hooks";

/** Format VND value with millions abbreviation: 100,000,000 → "100.0tr" */
function formatVND(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}tỷ`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}tr`;
  }
  return value.toLocaleString("vi-VN");
}

/** Format full VND value: 100,000,000 → "100,000,000 ₫" */
function formatVNDFull(value: number): string {
  return `${value.toLocaleString("vi-VN")} ₫`;
}

/** Format date string "2025-01-15" → "15/01" */
function formatDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

interface ComparisonTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color: string }>;
  label?: string;
}

function ComparisonTooltip({ active, payload, label }: ComparisonTooltipProps) {
  if (!active || !payload || !payload.length || !label) return null;
  const parts = label.split("-");
  const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
  return (
    <div className="rounded-md border bg-background px-3 py-2 shadow-md text-sm">
      <p className="text-muted-foreground mb-1">{formattedDate}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color }} className="font-semibold">
          {entry.name}: {formatVNDFull(entry.value)}
        </p>
      ))}
    </div>
  );
}

function pnlColor(value: number): string {
  return value >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
}

function betterClass(a: number, b: number): [string, string] {
  if (a > b) return ["font-semibold text-green-600 dark:text-green-400", ""];
  if (b > a) return ["", "font-semibold text-green-600 dark:text-green-400"];
  return ["", ""];
}

export function ComparisonSection() {
  const { data, isLoading } = useComparison();

  const mergedData = useMemo(() => {
    if (!data) return [];
    const dateMap = new Map<string, { date: string; ai?: number; user?: number }>();
    data.ai_equity_history.forEach((p) => {
      const entry = dateMap.get(p.date) || { date: p.date };
      entry.ai = p.equity;
      dateMap.set(p.date, entry);
    });
    data.user_equity_history.forEach((p) => {
      const entry = dateMap.get(p.date) || { date: p.date };
      entry.user = p.equity;
      dateMap.set(p.date, entry);
    });
    return Array.from(dateMap.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-[350px] w-full rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (!data) {
    return (
      <p className="text-sm text-muted-foreground py-12 text-center">
        Không có dữ liệu so sánh
      </p>
    );
  }

  const startingCapital = data.ai_portfolio.starting_capital;

  return (
    <div className="space-y-6">
      {/* A. Equity Overlay Chart */}
      <Card>
        <CardHeader>
          <CardTitle>📈 So sánh biểu đồ vốn</CardTitle>
        </CardHeader>
        <CardContent>
          {mergedData.length <= 1 ? (
            <p className="text-sm text-muted-foreground py-12 text-center">
              Chưa đủ dữ liệu để hiển thị biểu đồ
            </p>
          ) : (
            <div style={{ minHeight: 350 }}>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={mergedData}>
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDate}
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tickFormatter={formatVND}
                    tick={{ fontSize: 12 }}
                    width={70}
                  />
                  <Tooltip content={<ComparisonTooltip />} />
                  <Legend />
                  <ReferenceLine
                    y={startingCapital}
                    stroke="#9e9e9e"
                    strokeDasharray="5 5"
                    label={{
                      value: "Vốn ban đầu",
                      position: "right",
                      fontSize: 11,
                      fill: "#9e9e9e",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="ai"
                    stroke="#3b82f6"
                    name="AI Portfolio"
                    strokeWidth={2}
                    dot={mergedData.length <= 20}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="user"
                    stroke="#f59e0b"
                    name="Danh mục thủ công"
                    strokeWidth={2}
                    dot={mergedData.length <= 20}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* B. Portfolio Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">🤖 AI Portfolio</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tổng vốn</span>
              <span className="font-semibold">{formatVNDFull(data.ai_portfolio.total_equity)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lãi/Lỗ</span>
              <span className={`font-semibold ${pnlColor(data.ai_portfolio.total_pnl)}`}>
                {data.ai_portfolio.total_pnl >= 0 ? "+" : ""}{formatVNDFull(data.ai_portfolio.total_pnl)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">%</span>
              <span className={`font-semibold ${pnlColor(data.ai_portfolio.total_pnl_pct)}`}>
                {data.ai_portfolio.total_pnl_pct >= 0 ? "+" : ""}{data.ai_portfolio.total_pnl_pct.toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Số vị thế</span>
              <span>{data.ai_portfolio.position_count}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">👤 Danh mục thủ công</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tổng vốn</span>
              <span className="font-semibold">{formatVNDFull(data.user_portfolio.total_equity)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Lãi/Lỗ</span>
              <span className={`font-semibold ${pnlColor(data.user_portfolio.total_pnl)}`}>
                {data.user_portfolio.total_pnl >= 0 ? "+" : ""}{formatVNDFull(data.user_portfolio.total_pnl)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">%</span>
              <span className={`font-semibold ${pnlColor(data.user_portfolio.total_pnl_pct)}`}>
                {data.user_portfolio.total_pnl_pct >= 0 ? "+" : ""}{data.user_portfolio.total_pnl_pct.toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Số vị thế</span>
              <span>{data.user_portfolio.position_count}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* C. Metrics Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle>📊 So sánh chỉ số</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Chỉ số</TableHead>
                <TableHead className="text-right">🤖 AI</TableHead>
                <TableHead className="text-right">👤 Thủ công</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(() => {
                const rows: Array<{ label: string; ai: string; user: string; aiBetter: boolean; userBetter: boolean }> = [
                  {
                    label: "Tổng giao dịch",
                    ai: String(data.ai_stats.total_trades),
                    user: String(data.user_stats.total_trades),
                    aiBetter: false,
                    userBetter: false,
                  },
                  {
                    label: "Số lệnh AI",
                    ai: String(data.ai_stats.ai_trades),
                    user: String(data.user_stats.ai_trades),
                    aiBetter: false,
                    userBetter: false,
                  },
                  {
                    label: "Số lệnh thủ công",
                    ai: String(data.ai_stats.manual_trades),
                    user: String(data.user_stats.manual_trades),
                    aiBetter: false,
                    userBetter: false,
                  },
                  (() => {
                    const [ac, uc] = betterClass(data.ai_stats.ai_win_rate, data.user_stats.manual_win_rate);
                    return {
                      label: "Tỷ lệ thắng",
                      ai: `${data.ai_stats.ai_win_rate.toFixed(1)}%`,
                      user: `${data.user_stats.manual_win_rate.toFixed(1)}%`,
                      aiBetter: ac !== "",
                      userBetter: uc !== "",
                    };
                  })(),
                  (() => {
                    const [ac, uc] = betterClass(data.ai_stats.ai_avg_return_pct, data.user_stats.manual_avg_return_pct);
                    return {
                      label: "Lợi nhuận TB/lệnh",
                      ai: `${data.ai_stats.ai_avg_return_pct.toFixed(1)}%`,
                      user: `${data.user_stats.manual_avg_return_pct.toFixed(1)}%`,
                      aiBetter: ac !== "",
                      userBetter: uc !== "",
                    };
                  })(),
                  (() => {
                    const [ac, uc] = betterClass(data.ai_stats.ai_total_pnl, data.user_stats.manual_total_pnl);
                    return {
                      label: "Tổng lãi/lỗ",
                      ai: formatVND(data.ai_stats.ai_total_pnl),
                      user: formatVND(data.user_stats.manual_total_pnl),
                      aiBetter: ac !== "",
                      userBetter: uc !== "",
                    };
                  })(),
                ];

                return rows.map((row) => (
                  <TableRow key={row.label}>
                    <TableCell className="font-medium">{row.label}</TableCell>
                    <TableCell className={`text-right ${row.aiBetter ? "font-semibold text-green-600 dark:text-green-400" : ""}`}>
                      {row.ai}
                    </TableCell>
                    <TableCell className={`text-right ${row.userBetter ? "font-semibold text-green-600 dark:text-green-400" : ""}`}>
                      {row.user}
                    </TableCell>
                  </TableRow>
                ));
              })()}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
