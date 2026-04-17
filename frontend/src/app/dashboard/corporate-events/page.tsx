"use client";

import { Calendar } from "lucide-react";
import { CorporateEventsCalendar } from "@/components/corporate-events-calendar";

export default function CorporateEventsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Calendar className="size-6" />
          Lịch sự kiện doanh nghiệp
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Cổ tức, thưởng cổ phiếu và phát hành quyền mua
        </p>
      </div>
      <CorporateEventsCalendar />
    </div>
  );
}
