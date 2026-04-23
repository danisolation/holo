"use client";

import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import type { DailyPickResponse } from "@/lib/api";

interface AlmostSelectedListProps {
  tickers: DailyPickResponse[];
}

export function AlmostSelectedList({ tickers }: AlmostSelectedListProps) {
  if (tickers.length === 0) return null;

  return (
    <Accordion>
      <AccordionItem>
        <AccordionTrigger className="text-sm">
          Mã suýt được chọn ({tickers.length} mã)
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-0">
            {tickers.map((ticker) => (
              <div
                key={ticker.ticker_symbol}
                className="flex justify-between items-center py-2 border-b border-border/50 last:border-0"
              >
                <span className="font-mono text-sm font-bold">
                  {ticker.ticker_symbol}
                </span>
                <span className="text-sm text-muted-foreground">
                  {ticker.rejection_reason ?? "—"}
                </span>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
