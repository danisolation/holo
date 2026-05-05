"use client";

import { Star, Plus, Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { migrateWatchlist } from "@/lib/api";

export const VN30_TICKERS = [
  "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
  "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
  "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
] as const;

export function Vn30Preset() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => migrateWatchlist([...VN30_TICKERS]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12 text-center gap-4">
        <Star className="size-10 text-amber-500" />
        <div>
          <p className="font-medium mb-1">Bắt đầu với VN30 blue-chips</p>
          <p className="text-sm text-muted-foreground">
            Thêm 30 mã blue-chip hàng đầu sàn HOSE vào danh mục theo dõi chỉ với một click.
          </p>
        </div>
        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Đang thêm...
            </>
          ) : (
            <>
              <Plus className="size-4" />
              Thêm VN30 vào danh mục
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
