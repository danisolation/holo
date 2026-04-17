"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useExchangeStore, type Exchange } from "@/lib/store";

const EXCHANGES: { value: Exchange; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "HOSE", label: "HOSE" },
  { value: "HNX", label: "HNX" },
  { value: "UPCOM", label: "UPCOM" },
];

export function ExchangeFilter() {
  const { exchange, setExchange } = useExchangeStore();

  return (
    <Tabs
      value={exchange}
      onValueChange={(v) => setExchange(v as Exchange)}
    >
      <TabsList className="h-9">
        {EXCHANGES.map((ex) => (
          <TabsTrigger
            key={ex.value}
            value={ex.value}
            className="text-sm"
          >
            {ex.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
