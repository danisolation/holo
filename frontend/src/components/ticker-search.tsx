"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import {
  CommandDialog,
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { useTickers } from "@/lib/hooks";
import { postBehaviorEvent } from "@/lib/api";
import { getRecentSearches, addRecentSearch } from "@/lib/recent-searches";

export function TickerSearch() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { data: tickers } = useTickers(undefined, undefined, 500);
  const [recentSearches, setRecentSearches] = useState<Array<{ symbol: string; name: string }>>([]);

  useEffect(() => {
    if (open) {
      setRecentSearches(getRecentSearches());
    }
  }, [open]);

  const handleSelect = useCallback(
    (symbol: string) => {
      setOpen(false);
      const ticker = tickers?.find((t) => t.symbol === symbol);
      if (ticker) {
        addRecentSearch({ symbol: ticker.symbol, name: ticker.name });
      }
      postBehaviorEvent({ event_type: "search_click", ticker_symbol: symbol }).catch(() => {});
      router.push(`/ticker/${symbol}`);
    },
    [router, tickers]
  );

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="gap-2 text-muted-foreground w-48 justify-start"
        onClick={() => setOpen(true)}
      >
        <Search className="size-4" />
        <span className="text-sm">Tìm mã CK...</span>
        <kbd className="ml-auto pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
          ⌘K
        </kbd>
      </Button>

      <CommandDialog open={open} onOpenChange={setOpen} title="Tìm mã chứng khoán" description="Nhập mã hoặc tên công ty">
        <Command shouldFilter={true}>
          <CommandInput placeholder="Nhập mã CK hoặc tên công ty..." />
          <CommandList>
            <CommandEmpty>Không tìm thấy mã nào.</CommandEmpty>
            {recentSearches.length > 0 && (
              <CommandGroup heading="Tìm kiếm gần đây">
                {recentSearches.map((recent) => (
                  <CommandItem
                    key={`recent-${recent.symbol}`}
                    value={`${recent.symbol} ${recent.name}`}
                    onSelect={() => handleSelect(recent.symbol)}
                    className="cursor-pointer"
                  >
                    <span className="font-mono font-bold text-sm w-16">
                      {recent.symbol}
                    </span>
                    <span className="text-muted-foreground text-sm truncate">
                      {recent.name}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            <CommandGroup heading="Mã chứng khoán">
              {tickers?.map((ticker) => (
                <CommandItem
                  key={ticker.symbol}
                  value={`${ticker.symbol} ${ticker.name}`}
                  onSelect={() => handleSelect(ticker.symbol)}
                  className="cursor-pointer"
                >
                  <span className="font-mono font-bold text-sm w-16">
                    {ticker.symbol}
                  </span>
                  <span className="text-muted-foreground text-sm truncate">
                    {ticker.name}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
