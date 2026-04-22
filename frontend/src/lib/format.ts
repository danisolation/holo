export function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

export function formatCompactVND(value: number): string {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

export function formatDateVN(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}
