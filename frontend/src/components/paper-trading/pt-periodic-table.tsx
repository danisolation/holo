"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { usePaperPeriodic } from "@/lib/hooks";

function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

export function PTPeriodicTable() {
  const [period, setPeriod] = useState<"weekly" | "monthly">("weekly");
  const { data, isLoading } = usePaperPeriodic(period);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <CardTitle className="text-lg font-semibold">Tổng hợp theo kỳ</CardTitle>
          <Tabs
            value={period}
            onValueChange={(v) => setPeriod(v as "weekly" | "monthly")}
            className="sm:ml-auto"
          >
            <TabsList className="h-7">
              <TabsTrigger value="weekly" className="text-xs px-2">
                Tuần
              </TabsTrigger>
              <TabsTrigger value="monthly" className="text-xs px-2">
                Tháng
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full rounded-lg" />
        ) : !data?.length ? (
          <div className="flex items-center justify-center h-48">
            <p className="text-sm text-muted-foreground">
              Chưa có dữ liệu tổng hợp.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kỳ</TableHead>
                <TableHead className="text-right">Số lệnh</TableHead>
                <TableHead className="text-right">Thắng</TableHead>
                <TableHead className="text-right">Thua</TableHead>
                <TableHead className="text-right">Tỷ lệ thắng</TableHead>
                <TableHead className="text-right">P&L</TableHead>
                <TableHead className="text-right">TB R:R</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item) => (
                <TableRow key={item.period}>
                  <TableCell className="font-medium">{item.period}</TableCell>
                  <TableCell className="text-right">{item.total_trades}</TableCell>
                  <TableCell className="text-right text-[#26a69a]">
                    {item.wins}
                  </TableCell>
                  <TableCell className="text-right text-[#ef5350]">
                    {item.losses}
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant={item.win_rate >= 50 ? "default" : "destructive"}>
                      {item.win_rate.toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono ${
                      item.total_pnl >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                    }`}
                  >
                    {item.total_pnl >= 0 ? "+" : ""}
                    {formatVND(item.total_pnl)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {item.avg_rr.toFixed(2)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
