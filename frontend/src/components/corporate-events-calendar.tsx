"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useCorporateEvents } from "@/lib/hooks";
import type { CorporateEventResponse } from "@/lib/api";

// --- Constants ---

const DAY_HEADERS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

const EVENT_TYPE_LABELS: Record<string, string> = {
  CASH_DIVIDEND: "Cổ tức tiền",
  STOCK_DIVIDEND: "Cổ tức CP",
  BONUS_SHARES: "Thưởng CP",
  RIGHTS_ISSUE: "Quyền mua",
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  CASH_DIVIDEND: "bg-event-cash-dividend",
  STOCK_DIVIDEND: "bg-event-stock-dividend",
  BONUS_SHARES: "bg-event-bonus-shares",
  RIGHTS_ISSUE: "bg-event-rights-issue",
};

const EVENT_TYPE_BADGE_CLASSES: Record<string, string> = {
  CASH_DIVIDEND:
    "border-[var(--event-cash-dividend)] text-[var(--event-cash-dividend)] bg-[var(--event-cash-dividend)]/10",
  STOCK_DIVIDEND:
    "border-[var(--event-stock-dividend)] text-[var(--event-stock-dividend)] bg-[var(--event-stock-dividend)]/10",
  BONUS_SHARES:
    "border-[var(--event-bonus-shares)] text-[var(--event-bonus-shares)] bg-[var(--event-bonus-shares)]/10",
  RIGHTS_ISSUE:
    "border-[var(--event-rights-issue)] text-[var(--event-rights-issue)] bg-[var(--event-rights-issue)]/10",
};

const FILTER_TABS = [
  { value: "all", label: "Tất cả" },
  { value: "CASH_DIVIDEND", label: "Cổ tức tiền" },
  { value: "STOCK_DIVIDEND", label: "Cổ tức CP" },
  { value: "BONUS_SHARES", label: "Thưởng CP" },
  { value: "RIGHTS_ISSUE", label: "Quyền mua" },
];

// --- Helpers ---

function formatMonth(year: number, month: number): string {
  return `${year}-${String(month + 1).padStart(2, "0")}`;
}

function formatDateVN(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

function getCalendarDays(year: number, month: number) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const daysInMonth = lastDay.getDate();

  // Monday=0, Sunday=6
  let startWeekday = firstDay.getDay() - 1;
  if (startWeekday < 0) startWeekday = 6;

  const days: { date: number; month: number; year: number; isCurrentMonth: boolean }[] = [];

  // Previous month padding
  const prevMonthLastDay = new Date(year, month, 0).getDate();
  for (let i = startWeekday - 1; i >= 0; i--) {
    const d = prevMonthLastDay - i;
    const pm = month === 0 ? 11 : month - 1;
    const py = month === 0 ? year - 1 : year;
    days.push({ date: d, month: pm, year: py, isCurrentMonth: false });
  }

  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    days.push({ date: d, month, year, isCurrentMonth: true });
  }

  // Next month padding (fill to 42 cells = 6 rows)
  const remaining = 42 - days.length;
  for (let d = 1; d <= remaining; d++) {
    const nm = month === 11 ? 0 : month + 1;
    const ny = month === 11 ? year + 1 : year;
    days.push({ date: d, month: nm, year: ny, isCurrentMonth: false });
  }

  return days;
}

function dateKey(year: number, month: number, date: number): string {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(date).padStart(2, "0")}`;
}

function eventDetail(event: CorporateEventResponse): string {
  if (event.event_type === "CASH_DIVIDEND" && event.dividend_amount != null) {
    return `${new Intl.NumberFormat("vi-VN").format(event.dividend_amount)} VNĐ/CP`;
  }
  if (event.ratio != null) {
    return `Tỷ lệ: ${event.ratio}:100`;
  }
  return "";
}

// --- Sub-components ---

function EventDot({ eventType }: { eventType: string }) {
  return (
    <span
      className={`inline-block size-1.5 rounded-full ${EVENT_TYPE_COLORS[eventType] ?? "bg-muted-foreground"}`}
    />
  );
}

function DayPopoverContent({ events }: { events: CorporateEventResponse[] }) {
  if (events.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center">
        Không có sự kiện
      </p>
    );
  }

  const dateLabel = formatDateVN(events[0].ex_date);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">Ngày {dateLabel}</span>
        <Badge variant="secondary" className="text-xs">
          {events.length} sự kiện
        </Badge>
      </div>
      <Separator />
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {events.map((event) => (
          <div key={event.id} className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={`text-xs ${EVENT_TYPE_BADGE_CLASSES[event.event_type] ?? ""}`}
              >
                {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
              </Badge>
              <Link
                href={`/ticker/${event.symbol}`}
                className="font-mono font-semibold text-sm hover:underline"
              >
                {event.symbol}
              </Link>
            </div>
            <p className="text-xs text-muted-foreground">
              Ex-date: {formatDateVN(event.ex_date)}
            </p>
            {eventDetail(event) && (
              <p className="text-xs text-muted-foreground font-mono">
                {eventDetail(event)}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Main Component ---

export function CorporateEventsCalendar() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [selectedType, setSelectedType] = useState("all");

  const monthStr = formatMonth(year, month);
  const fetchParams = useMemo(
    () => ({
      month: monthStr,
      ...(selectedType !== "all" ? { type: selectedType } : {}),
    }),
    [monthStr, selectedType],
  );

  const { data: events, isLoading } = useCorporateEvents(fetchParams);

  // Group events by date key
  const eventsByDate = useMemo(() => {
    const map = new Map<string, CorporateEventResponse[]>();
    if (!events) return map;
    for (const event of events) {
      const key = event.ex_date.split("T")[0]; // YYYY-MM-DD
      const existing = map.get(key) ?? [];
      existing.push(event);
      map.set(key, existing);
    }
    return map;
  }, [events]);

  const calendarDays = useMemo(
    () => getCalendarDays(year, month),
    [year, month],
  );

  const today = new Date();
  const todayKey = dateKey(today.getFullYear(), today.getMonth(), today.getDate());

  function prevMonth() {
    if (month === 0) {
      setYear((y) => y - 1);
      setMonth(11);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (month === 11) {
      setYear((y) => y + 1);
      setMonth(0);
    } else {
      setMonth((m) => m + 1);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold">
          Lịch sự kiện doanh nghiệp
        </CardTitle>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="xs" onClick={prevMonth}>
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-sm font-semibold min-w-[120px] text-center">
            Tháng {String(month + 1).padStart(2, "0")}/{year}
          </span>
          <Button variant="ghost" size="xs" onClick={nextMonth}>
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Event type filter tabs */}
        <Tabs
          value={selectedType}
          onValueChange={setSelectedType}
        >
          <TabsList variant="line" className="h-9">
            {FILTER_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value} className="text-sm gap-1.5">
                {tab.value !== "all" && <EventDot eventType={tab.value} />}
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Calendar grid */}
        {isLoading ? (
          <Skeleton className="h-[320px] w-full rounded-lg" />
        ) : (
          <div>
            {/* Day-of-week headers */}
            <div className="grid grid-cols-7 mb-1">
              {DAY_HEADERS.map((d) => (
                <div
                  key={d}
                  className="text-center text-xs text-muted-foreground py-1"
                >
                  {d}
                </div>
              ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7 gap-px">
              {calendarDays.map((day, idx) => {
                const key = dateKey(day.year, day.month, day.date);
                const dayEvents = eventsByDate.get(key) ?? [];
                const hasEvents = dayEvents.length > 0;
                const isToday = key === todayKey;

                const cell = (
                  <div
                    className={`
                      relative min-h-[40px] p-1 rounded-md transition-colors
                      ${day.isCurrentMonth ? "" : "opacity-40"}
                      ${isToday ? "ring-2 ring-primary" : ""}
                      ${hasEvents ? "cursor-pointer hover:bg-muted" : "cursor-default"}
                    `}
                  >
                    <span className="text-sm">{day.date}</span>
                    {hasEvents && (
                      <div className="flex items-center gap-0.5 mt-0.5 flex-wrap">
                        {dayEvents.slice(0, 4).map((ev, i) => (
                          <EventDot key={i} eventType={ev.event_type} />
                        ))}
                        {dayEvents.length > 4 && (
                          <span className="text-[10px] text-muted-foreground">
                            +{dayEvents.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );

                if (hasEvents) {
                  return (
                    <Popover key={idx}>
                      <PopoverTrigger
                        render={<div role="button" tabIndex={0} />}
                      >
                        {cell}
                      </PopoverTrigger>
                      <PopoverContent
                        side="bottom"
                        align="start"
                        className="w-72 p-4"
                      >
                        <DayPopoverContent events={dayEvents} />
                      </PopoverContent>
                    </Popover>
                  );
                }

                return <div key={idx}>{cell}</div>;
              })}
            </div>

            {/* Empty state */}
            {events && events.length === 0 && (
              <div className="text-center text-sm text-muted-foreground py-8">
                Không có sự kiện trong tháng này
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
