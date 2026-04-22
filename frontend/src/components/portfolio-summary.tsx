"use client";

import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Briefcase,
  Coins,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolioSummary } from "@/lib/hooks";
import { formatVND } from "@/lib/format";

export function PortfolioSummary() {
  const { data, isLoading } = usePortfolioSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-muted-foreground text-sm">
          Chưa có dữ liệu danh mục
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      label: "Tổng đầu tư",
      value: `${formatVND(data.total_invested)} ₫`,
      icon: DollarSign,
      color: "text-blue-500",
    },
    {
      label: "Giá trị thị trường",
      value: data.total_market_value != null ? `${formatVND(data.total_market_value)} ₫` : "—",
      icon: BarChart3,
      color: "text-purple-500",
    },
    {
      label: "Lời/Lỗ đã chốt",
      value: `${formatVND(data.total_realized_pnl)} ₫`,
      icon: data.total_realized_pnl >= 0 ? TrendingUp : TrendingDown,
      color: data.total_realized_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]",
    },
    {
      label: "Tổng lợi nhuận",
      value: data.total_return_pct != null ? `${data.total_return_pct.toFixed(2)}%` : "—",
      icon: Briefcase,
      color:
        data.total_return_pct != null && data.total_return_pct >= 0
          ? "text-[#26a69a]"
          : "text-[#ef5350]",
    },
    {
      label: "Cổ tức nhận",
      value: `${formatVND(data.dividend_income)} ₫`,
      icon: Coins,
      color: "text-[#26a69a]",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      {cards.map((card, index) => (
        <Card
          key={card.label}
          size="sm"
          className={index === cards.length - 1 ? "col-span-2 lg:col-span-1" : undefined}
        >
          <CardContent className="flex items-center gap-3">
            <card.icon className={`size-8 shrink-0 ${card.color}`} />
            <div className="min-w-0">
              <p className="text-lg font-bold truncate">{card.value}</p>
              <p className="text-xs text-muted-foreground">{card.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
