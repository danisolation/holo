"use client";

import { useState, useEffect } from "react";
import { Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { usePaperConfig, useUpdatePaperConfig } from "@/lib/hooks";

export function PTSettingsForm() {
  const { data: config, isLoading } = usePaperConfig();
  const updateConfig = useUpdatePaperConfig();

  const [capital, setCapital] = useState("");
  const [autoTrack, setAutoTrack] = useState(true);
  const [minConfidence, setMinConfidence] = useState(5);

  useEffect(() => {
    if (config) {
      setCapital(String(config.initial_capital));
      setAutoTrack(config.auto_track_enabled);
      setMinConfidence(config.min_confidence_threshold);
    }
  }, [config]);

  const handleSave = () => {
    updateConfig.mutate({
      initial_capital: Number(capital),
      auto_track_enabled: autoTrack,
      min_confidence_threshold: minConfidence,
    });
  };

  if (isLoading) {
    return <Skeleton className="h-48 rounded-xl" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Cài đặt mô phỏng</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-w-md space-y-6">
          {/* Initial capital */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Vốn ban đầu (VND)</label>
            <Input
              type="number"
              min={1000000}
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className="font-mono"
            />
          </div>

          {/* Auto-track toggle */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Tự động theo dõi tín hiệu
            </label>
            <div className="flex gap-2">
              <Button
                variant={autoTrack ? "default" : "outline"}
                size="sm"
                onClick={() => setAutoTrack(true)}
              >
                Bật
              </Button>
              <Button
                variant={!autoTrack ? "default" : "outline"}
                size="sm"
                onClick={() => setAutoTrack(false)}
              >
                Tắt
              </Button>
            </div>
          </div>

          {/* Min confidence threshold */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Ngưỡng confidence tối thiểu
            </label>
            <div className="flex items-center gap-3">
              <Input
                type="number"
                min={1}
                max={10}
                value={minConfidence}
                onChange={(e) => setMinConfidence(Number(e.target.value))}
                className="font-mono w-20"
              />
              <span className="text-xs text-muted-foreground">
                1-10 (chỉ theo dõi tín hiệu có score ≥ giá trị này)
              </span>
            </div>
          </div>

          {/* Save button */}
          <Button onClick={handleSave} disabled={updateConfig.isPending}>
            {updateConfig.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Đang lưu...
              </>
            ) : (
              <>
                <Save className="mr-2 size-4" />
                Lưu cài đặt
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
