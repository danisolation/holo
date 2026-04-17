import { create } from "zustand";
import { persist } from "zustand/middleware";

interface WatchlistState {
  watchlist: string[];
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  isInWatchlist: (symbol: string) => boolean;
}

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      watchlist: [],

      addToWatchlist: (symbol: string) => {
        const upper = symbol.toUpperCase();
        set((state) => {
          if (state.watchlist.includes(upper)) return state;
          return { watchlist: [...state.watchlist, upper] };
        });
      },

      removeFromWatchlist: (symbol: string) => {
        const upper = symbol.toUpperCase();
        set((state) => ({
          watchlist: state.watchlist.filter((s) => s !== upper),
        }));
      },

      isInWatchlist: (symbol: string) => {
        return get().watchlist.includes(symbol.toUpperCase());
      },
    }),
    {
      name: "holo-watchlist",
    },
  ),
);

export type Exchange = "all" | "HOSE" | "HNX" | "UPCOM";

interface ExchangeFilterState {
  exchange: Exchange;
  setExchange: (exchange: Exchange) => void;
}

export const useExchangeStore = create<ExchangeFilterState>()(
  persist(
    (set) => ({
      exchange: "all" as Exchange,
      setExchange: (exchange: Exchange) => set({ exchange }),
    }),
    {
      name: "holo-exchange-filter",
    },
  ),
);
