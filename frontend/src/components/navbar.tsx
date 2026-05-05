"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { BarChart3, Menu, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { TickerSearch } from "@/components/ticker-search";
import { ConnectionStatusIndicator } from "@/components/connection-status";
import { useRealtimePrices } from "@/lib/use-realtime-prices";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Tổng quan", description: "Bảng giá & heatmap thị trường" },
  { href: "/discovery", label: "Khám phá", description: "Gợi ý cổ phiếu từ AI, cập nhật hàng ngày" },
  { href: "/watchlist", label: "Danh mục", description: "Danh mục theo dõi & phân tích AI" },
  { href: "/coach", label: "Huấn luyện", description: "AI coach & nhật ký giao dịch" },
  { href: "/journal", label: "Nhật ký", description: "Lịch sử giao dịch & hiệu suất" },
  { href: "/dashboard/health", label: "Hệ thống", description: "Trạng thái hệ thống & API" },
];

export function Navbar() {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const { status, subscribedCount } = useRealtimePrices([]);

  return (
    <header data-testid="navbar" className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center gap-4 px-4 mx-auto max-w-7xl">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <BarChart3 className="size-6 text-primary" />
          <span className="text-lg font-bold tracking-tight">Holo</span>
        </Link>

        {/* Desktop Navigation */}
        <nav data-testid="nav-desktop" className="hidden md:flex items-center gap-1 ml-4">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              title={link.description}
              className={cn(
                "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                pathname === link.href
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right side: Search + Theme toggle + Mobile menu */}
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden sm:block">
            <TickerSearch />
          </div>

          {/* Real-time connection status */}
          <ConnectionStatusIndicator
            status={status}
            subscribedCount={subscribedCount}
          />

          {/* Dark mode toggle */}
          <Button
            data-testid="theme-toggle"
            variant="ghost"
            size="icon-sm"
            className="relative"
            onClick={() =>
              setTheme(resolvedTheme === "dark" ? "light" : "dark")
            }
          >
            <Sun className="size-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute size-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Chuyển chế độ sáng/tối</span>
          </Button>

          {/* Mobile hamburger menu */}
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="md:hidden"
                />
              }
            >
              <Menu className="size-5" />
              <span className="sr-only">Menu</span>
            </SheetTrigger>
            <SheetContent side="left">
              <SheetHeader>
                <SheetTitle>
                  <Link
                    href="/"
                    className="flex items-center gap-2"
                    onClick={() => setOpen(false)}
                  >
                    <BarChart3 className="size-5 text-primary" />
                    <span className="font-bold">Holo</span>
                  </Link>
                </SheetTitle>
                <SheetDescription>Điều hướng</SheetDescription>
              </SheetHeader>
              <nav className="flex flex-col gap-1 px-4">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                      pathname === link.href
                        ? "bg-muted text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                    )}
                  >
                    <span>{link.label}</span>
                    <span className="block text-xs font-normal text-muted-foreground/70 mt-0.5">{link.description}</span>
                  </Link>
                ))}
              </nav>
              <div className="px-4 mt-4 sm:hidden">
                <TickerSearch />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
