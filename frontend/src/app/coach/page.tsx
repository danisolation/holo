"use client";

import { Calendar, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDailyPicks, useProfile } from "@/lib/hooks";
import { formatVND } from "@/lib/format";
import { PickCard, PickCardSkeleton } from "@/components/pick-card";
import { AlmostSelectedList } from "@/components/almost-selected-list";
import { ProfileSettingsCard } from "@/components/profile-settings-card";

export default function CoachPage() {
  const { data: picksData, isLoading, isError, refetch } = useDailyPicks();
  const { data: profile } = useProfile();

  return (
    <div className="space-y-8">
      {/* Section 1 — Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gợi ý hôm nay</h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI chọn {picksData?.picks.length ?? 0} mã phù hợp với vốn{" "}
            {formatVND(profile?.capital ?? 50_000_000)}đ
          </p>
        </div>
        <ProfileSettingsCard />
      </div>

      {/* Section 2 — Pick card grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <PickCardSkeleton key={i} />
          ))}
        </div>
      ) : isError ? (
        <Card className="max-w-md mx-auto">
          <CardContent className="flex flex-col items-center text-center py-12">
            <AlertTriangle className="size-12 text-destructive/60 mb-4" />
            <h2 className="text-lg font-bold">Không thể tải gợi ý</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Đã xảy ra lỗi khi tải dữ liệu. Vui lòng thử lại.
            </p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => refetch()}
            >
              Thử lại
            </Button>
          </CardContent>
        </Card>
      ) : picksData && picksData.picks.length === 0 ? (
        <Card className="max-w-md mx-auto">
          <CardContent className="flex flex-col items-center text-center py-12">
            <Calendar className="size-12 text-muted-foreground/40 mb-4" />
            <h2 className="text-lg font-bold">Chưa có gợi ý hôm nay</h2>
            <p className="text-sm text-muted-foreground mt-2 max-w-md">
              Gợi ý sẽ được tạo sau khi phân tích AI chạy xong (~17:00 mỗi ngày
              giao dịch).
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {picksData?.picks.map((pick) => (
            <PickCard key={pick.ticker_symbol} pick={pick} />
          ))}
        </div>
      )}

      {/* Section 3 — Almost selected */}
      {picksData?.almost_selected && picksData.almost_selected.length > 0 && (
        <AlmostSelectedList tickers={picksData.almost_selected} />
      )}
    </div>
  );
}
