"use client";

import { useState } from "react";
import { useTriggerJob } from "@/lib/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Play, Loader2 } from "lucide-react";

const JOBS = [
  { name: "crawl", label: "Crawl giá", description: "Cập nhật giá cổ phiếu từ VNDirect" },
  { name: "indicators", label: "Tính chỉ báo", description: "Tính toán RSI, MACD, Bollinger, SMA" },
  { name: "ai", label: "Phân tích AI", description: "Chạy phân tích kỹ thuật + cơ bản bằng Gemini" },
  { name: "news", label: "Crawl tin", description: "Thu thập tin tức từ CafeF" },
  { name: "sentiment", label: "Tâm lý", description: "Phân tích sentiment tin tức" },
  { name: "combined", label: "Tổng hợp", description: "Phân tích tổng hợp đa chiều" },
];

export function JobTriggerButtons() {
  const trigger = useTriggerJob();
  const [confirmJob, setConfirmJob] = useState<string | null>(null);

  const handleTrigger = async (jobName: string) => {
    await trigger.mutateAsync(jobName);
    setConfirmJob(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Play className="size-4" />
          Chạy thủ công
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {JOBS.map((job) => (
            <Dialog key={job.name} open={confirmJob === job.name} onOpenChange={(open) => setConfirmJob(open ? job.name : null)}>
              <DialogTrigger
                render={
                  <Button variant="outline" size="sm" className="w-full justify-start gap-2">
                    <Play className="size-3" />
                    {job.label}
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Xác nhận chạy {job.label}?</DialogTitle>
                  <DialogDescription>{job.description}</DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setConfirmJob(null)}>Hủy</Button>
                  <Button onClick={() => handleTrigger(job.name)} disabled={trigger.isPending}>
                    {trigger.isPending ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
                    Chạy
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
