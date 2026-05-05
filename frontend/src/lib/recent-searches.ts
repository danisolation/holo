const STORAGE_KEY = "holo-recent-searches";
const MAX_RECENT = 5;

export interface RecentSearch {
  symbol: string;
  name: string;
}

export function getRecentSearches(): RecentSearch[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

export function addRecentSearch(item: RecentSearch): void {
  try {
    const current = getRecentSearches();
    // Remove duplicate if exists, then prepend
    const filtered = current.filter((s) => s.symbol !== item.symbol);
    const updated = [item, ...filtered].slice(0, MAX_RECENT);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // Silently fail if localStorage unavailable
  }
}
