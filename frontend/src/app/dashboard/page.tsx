"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMarketOverview } from "@/lib/hooks";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

const PIE_COLORS: Record<string, string> = {
  "Tăng": "#26a69a",
  "Giảm": "#ef5350",
  "Đứng giá": "#888888",
};

export default function DashboardPage() {
  const { data: marketData } = useMarketOverview();

  const stats = useMemo(() => {
    if (!marketData) return null;

    const gainers = marketData.filter(
      (t) => t.change_pct != null && t.change_pct > 0,
    );
    const losers = marketData.filter(
      (t) => t.change_pct != null && t.change_pct < 0,
    );
    const unchanged = marketData.length - gainers.length - losers.length;

    const topGainers = [...gainers]
      .sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))
      .slice(0, 5);
    const topLosers = [...losers]
      .sort((a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0))
      .slice(0, 5);

    const pieData = [
      { name: "Tăng", value: gainers.length },
      { name: "Giảm", value: losers.length },
      { name: "Đứng giá", value: unchanged },
    ].filter((d) => d.value > 0);

    return {
      topGainers,
      topLosers,
      pieData,
    };
  }, [marketData]);

  return (
    <div className="space-y-8">
      {/* Page title */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Bảng điều khiển</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Phân tích nhanh và top biến động
        </p>
      </div>

      {/* Signal Distribution Pie Chart */}
      {stats && stats.pieData.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Phân bổ tăng/giảm</h3>
          <Card>
            <CardContent className="py-4">
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="value"
                      nameKey="name"
                      paddingAngle={2}
                    >
                      {stats.pieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={PIE_COLORS[entry.name] ?? "#888"}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "0.5rem",
                        color: "hsl(var(--popover-foreground))",
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {/* Top Movers */}
      {stats && (
        <section>
          <h3 className="text-lg font-semibold mb-3">Top biến động</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Top Gainers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#26a69a]">
                  <TrendingUp className="size-4" />
                  Top tăng
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {stats.topGainers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã tăng
                  </p>
                ) : (
                  stats.topGainers.map((t) => (
                    <Link
                      key={t.symbol}
                      href={`/ticker/${t.symbol}`}
                      className="flex items-center justify-between py-1.5 rounded-md px-2 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm">
                          {t.symbol}
                        </span>
                        <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                          {t.name}
                        </span>
                      </div>
                      <span className="font-mono text-sm text-[#26a69a]">
                        +{(t.change_pct ?? 0).toFixed(2)}%
                      </span>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Top Losers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#ef5350]">
                  <TrendingDown className="size-4" />
                  Top giảm
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {stats.topLosers.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Không có mã giảm
                  </p>
                ) : (
                  stats.topLosers.map((t) => (
                    <Link
                      key={t.symbol}
                      href={`/ticker/${t.symbol}`}
                      className="flex items-center justify-between py-1.5 rounded-md px-2 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm">
                          {t.symbol}
                        </span>
                        <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                          {t.name}
                        </span>
                      </div>
                      <span className="font-mono text-sm text-[#ef5350]">
                        {(t.change_pct ?? 0).toFixed(2)}%
                      </span>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      )}
    </div>
  );
}
