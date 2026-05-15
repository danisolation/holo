"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMarketOverview } from "@/lib/hooks";

interface SectorDrilldownProps {
  sectorName: string;
  onClose: () => void;
}

export function SectorDrilldown({ sectorName, onClose }: SectorDrilldownProps) {
  const { data, isLoading } = useMarketOverview();

  // Filter tickers by sector and sort by change_pct descending
  const tickers = (data ?? [])
    .filter((t) => t.sector === sectorName)
    .sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-base font-semibold">
          {sectorName}{" "}
          <span className="text-sm font-normal text-muted-foreground">
            ({tickers.length} mã)
          </span>
        </CardTitle>
        <Button variant="ghost" size="icon-sm" onClick={onClose}>
          <X className="size-4" />
          <span className="sr-only">Đóng</span>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 rounded-md" />
            ))}
          </div>
        ) : tickers.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            Không có dữ liệu mã trong ngành này
          </p>
        ) : (
          <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Mã</th>
                  <th className="py-2 pr-3 font-medium hidden sm:table-cell">
                    Tên
                  </th>
                  <th className="py-2 pr-3 font-medium text-right">Giá</th>
                  <th className="py-2 pr-3 font-medium text-right">
                    % Thay đổi
                  </th>
                  <th className="py-2 font-medium text-right hidden md:table-cell">
                    Vốn hóa
                  </th>
                </tr>
              </thead>
              <tbody>
                {tickers.map((ticker) => (
                  <tr
                    key={ticker.symbol}
                    className="border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="py-2 pr-3 font-mono font-bold">
                      {ticker.symbol}
                    </td>
                    <td className="py-2 pr-3 truncate max-w-[180px] hidden sm:table-cell">
                      {ticker.name}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono">
                      {ticker.last_price != null
                        ? ticker.last_price.toLocaleString("vi-VN")
                        : "—"}
                    </td>
                    <td
                      className={`py-2 pr-3 text-right font-mono font-medium ${
                        ticker.change_pct != null && ticker.change_pct > 0
                          ? "text-trading-bull"
                          : ticker.change_pct != null && ticker.change_pct < 0
                            ? "text-trading-bear"
                            : "text-muted-foreground"
                      }`}
                    >
                      {ticker.change_pct != null
                        ? `${ticker.change_pct >= 0 ? "+" : ""}${ticker.change_pct.toFixed(2)}%`
                        : "—"}
                    </td>
                    <td className="py-2 text-right font-mono text-muted-foreground hidden md:table-cell">
                      {ticker.market_cap != null
                        ? `${(ticker.market_cap / 1e9).toFixed(0)}B`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
