export function formatVND(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value));
}

/** Format stock price: DB stores in nghìn đồng → multiply ×1000 for VND display */
export function formatPrice(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.round(value * 1000));
}

export function formatCompactVND(value: number): string {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

export function formatDateVN(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}
