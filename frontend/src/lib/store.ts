import { create } from "zustand";
import { persist } from "zustand/middleware";

// Clean up stale localStorage from removed exchange filter feature
if (typeof window !== "undefined") {
  localStorage.removeItem("holo-exchange-filter");
}

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
