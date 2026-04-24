import { migrateWatchlist } from "@/lib/api";

// Clean up stale localStorage from removed exchange filter feature
if (typeof window !== "undefined") {
  localStorage.removeItem("holo-exchange-filter");
}

/**
 * One-time migration: move localStorage watchlist to server.
 * Returns true if migration was performed, false if not needed.
 */
export async function migrateLocalWatchlist(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const raw = localStorage.getItem("holo-watchlist");
  if (!raw) return false;

  try {
    const parsed = JSON.parse(raw);
    const symbols: string[] = parsed?.state?.watchlist ?? [];
    if (symbols.length === 0) {
      localStorage.removeItem("holo-watchlist");
      return false;
    }
    await migrateWatchlist(symbols);
    localStorage.removeItem("holo-watchlist");
    return true;
  } catch (err) {
    console.error("[watchlist-migration] Failed to migrate localStorage watchlist:", err);
    return false;
  }
}
