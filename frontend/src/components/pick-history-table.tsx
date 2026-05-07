"use client";

import { useState } from "react";
import { usePickHistory } from "@/lib/hooks";
import { formatVND, formatPrice, formatDateVN } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Sparkles, History, AlertTriangle } from "lucide-react";

function OutcomeBadge({ outcome }: { outcome: string }) {
  switch (outcome) {
    case "winner":
      return (
        <Badge className="text-[#26a69a] bg-[#26a69a]/10 border-transparent text-xs font-bold">
          Thắng
        </Badge>
      );
    case "loser":
      return (
        <Badge className="text-[#ef5350] bg-[#ef5350]/10 border-transparent text-xs font-bold">
          Thua
        </Badge>
      );
    case "expired":
      return (
        <Badge variant="outline" className="text-xs font-bold">
          Hết hạn
        </Badge>
      );
    case "pending":
    default:
      return (
        <Badge className="text-blue-600 bg-blue-600/10 border-transparent text-xs font-bold dark:text-blue-400 dark:bg-blue-400/10">
          Đang theo dõi
        </Badge>
      );
  }
}

function ReturnCell({ value }: { value: number | null }) {
  if (value === null) {
    return <span className="text-muted-foreground">—</span>;
  }
  if (value > 0) {
    return (
      <span className="text-[#26a69a] font-mono text-sm font-bold">
        +{value.toFixed(1)}%
      </span>
    );
  }
  if (value < 0) {
    return (
      <span className="text-[#ef5350] font-mono text-sm font-bold">
        {value.toFixed(1)}%
      </span>
    );
  }
  return (
    <span className="text-muted-foreground font-mono text-sm font-bold">
      0.0%
    </span>
  );
}

const FILTER_OPTIONS = [
  { label: "Tất cả", value: "all" },
  { label: "Thắng", value: "winner" },
  { label: "Thua", value: "loser" },
  { label: "Hết hạn", value: "expired" },
  { label: "Đang theo dõi", value: "pending" },
] as const;

export function PickHistoryTable() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("all");
  const { data, isLoading, isError, refetch } = usePickHistory({ page, status });

  const total = data?.total ?? 0;
  const perPage = data?.per_page ?? 20;
  const start = total === 0 ? 0 : (page - 1) * perPage + 1;
  const end = Math.min(page * perPage, total);

  function handleFilterChange(value: string) {
    setStatus(value);
    setPage(1);
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">Lịch sử gợi ý</h2>

      <Card>
        <CardContent>
          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {FILTER_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                variant={status === opt.value ? "default" : "outline"}
                size="sm"
                aria-pressed={status === opt.value}
                onClick={() => handleFilterChange(opt.value)}
              >
                {opt.label}
              </Button>
            ))}
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 rounded" />
              ))}
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertTriangle className="size-12 text-destructive/60" />
              <p className="text-lg font-bold mt-4">Không thể tải lịch sử</p>
              <p className="text-sm text-muted-foreground mt-2">
                Đã xảy ra lỗi khi tải dữ liệu lịch sử gợi ý. Vui lòng thử lại.
              </p>
              <Button variant="outline" className="mt-4" onClick={() => refetch()}>
                Thử lại
              </Button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && total === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <History className="size-12 text-muted-foreground/40" />
              <p className="text-lg font-bold mt-4">Chưa có lịch sử gợi ý</p>
              <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
                Lịch sử sẽ xuất hiện sau ngày giao dịch đầu tiên có gợi ý.
              </p>
            </div>
          )}

          {/* Data table */}
          {!isLoading && !isError && data && data.items.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-24">Ngày</TableHead>
                      <TableHead className="w-16">Mã</TableHead>
                      <TableHead className="w-10 text-center">#</TableHead>
                      <TableHead className="w-24 text-right">Giá vào</TableHead>
                      <TableHead className="w-20 text-right">Cắt lỗ</TableHead>
                      <TableHead className="w-20 text-right">Chốt lời</TableHead>
                      <TableHead className="w-28 text-center">Kết quả</TableHead>
                      <TableHead className="w-20 text-right">Lãi/Lỗ</TableHead>
                      <TableHead className="w-14 text-center">Ngày</TableHead>
                      <TableHead className="w-10 text-center">GD</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((pick) => (
                      <TableRow key={pick.id}>
                        <TableCell className="text-sm">
                          {formatDateVN(pick.pick_date)}
                        </TableCell>
                        <TableCell className="font-mono text-sm font-bold">
                          {pick.ticker_symbol}
                        </TableCell>
                        <TableCell className="font-mono text-sm font-bold text-center">
                          {pick.rank ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono text-sm font-bold text-right">
                          {pick.entry_price !== null ? formatPrice(pick.entry_price) : "—"}
                        </TableCell>
                        <TableCell className="font-mono text-sm text-[#ef5350] text-right">
                          {pick.stop_loss !== null ? formatPrice(pick.stop_loss) : "—"}
                        </TableCell>
                        <TableCell className="font-mono text-sm text-[#26a69a] text-right">
                          {pick.take_profit_1 !== null ? formatPrice(pick.take_profit_1) : "—"}
                        </TableCell>
                        <TableCell className="text-center">
                          <OutcomeBadge outcome={pick.pick_outcome} />
                        </TableCell>
                        <TableCell className="text-right">
                          <ReturnCell value={pick.actual_return_pct} />
                        </TableCell>
                        <TableCell className="font-mono text-sm text-center">
                          {pick.days_held !== null ? pick.days_held : "—"}
                        </TableCell>
                        <TableCell className="text-center">
                          {pick.has_trades && (
                            <span title="Đã giao dịch">
                              <Sparkles
                                className="size-4 text-blue-600 dark:text-blue-400 inline-block"
                                aria-hidden="true"
                              />
                              <span className="sr-only">Đã giao dịch</span>
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <nav
                className="flex items-center justify-between pt-4"
                aria-label="Phân trang lịch sử gợi ý"
              >
                <p className="text-sm text-muted-foreground">
                  Hiển thị {start}-{end} / {total} gợi ý
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Trước
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page * perPage >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Sau
                  </Button>
                </div>
              </nav>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
