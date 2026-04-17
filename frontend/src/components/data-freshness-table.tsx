"use client";

import { useDataFreshness } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Database } from "lucide-react";

function formatLatest(iso: string | null): string {
  if (!iso) return "Chưa có dữ liệu";
  const d = new Date(iso);
  return d.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function DataFreshnessTable() {
  const { data, isLoading, error } = useDataFreshness();

  if (isLoading) return <Skeleton className="h-48" />;
  if (error || !data) return <p className="text-sm text-muted-foreground">Không thể tải dữ liệu freshness.</p>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Database className="size-4" />
          Độ tươi dữ liệu
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nguồn dữ liệu</TableHead>
              <TableHead>Cập nhật cuối</TableHead>
              <TableHead>Ngưỡng (giờ)</TableHead>
              <TableHead>Trạng thái</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((item) => (
              <TableRow key={item.table_name}>
                <TableCell className="font-medium">{item.data_type}</TableCell>
                <TableCell>{formatLatest(item.latest)}</TableCell>
                <TableCell>{item.threshold_hours}h</TableCell>
                <TableCell>
                  <Badge variant={item.is_stale ? "destructive" : "default"}>
                    {item.is_stale ? "Cũ" : "Mới"}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
