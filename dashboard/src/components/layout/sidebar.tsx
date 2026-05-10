"use client";

import { cn } from "@/lib/utils";
import { useSidebar } from "@/contexts/sidebar-context";
import { useAuth } from "@/providers/auth-provider";
import {
  Activity,
  BarChart3,
  CandlestickChart,
  ChevronLeft,
  Coins,
  Landmark,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  Search,
  Settings,
  Signal,
  User,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/signals", label: "Sinyaller", icon: Signal },
  { href: "/orders", label: "Emirler", icon: ListOrdered },
  { href: "/trades", label: "İşlemler", icon: BarChart3 },
  { href: "/portfolio", label: "Portföy", icon: Wallet },
  { href: "/cryptos", label: "Kriptolar", icon: Coins },
  { href: "/pairs", label: "Takip Edilenler", icon: CandlestickChart },
  { href: "/screener", label: "Tarama", icon: Search },
  { href: "/binance", label: "Binance", icon: Landmark },
  { href: "/settings", label: "Ayarlar", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { username, logout } = useAuth();
  const { isOpen, isCollapsed, close, toggleCollapse } = useSidebar();

  const collapsed = isCollapsed;

  return (
    <>
      {/* Mobil overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 sm:hidden"
          onClick={close}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card transition-all duration-200",
          // Mobil: overlay, tam genişlik
          isOpen ? "translate-x-0" : "-translate-x-full",
          "w-56",
          // Desktop: her zaman görünür
          "sm:relative sm:translate-x-0 sm:z-auto",
          collapsed ? "sm:w-16" : "sm:w-56",
        )}
      >
        {/* Header */}
        <div className="flex h-14 items-center border-b border-border px-4">
          <Activity className="h-5 w-5 shrink-0 text-primary" />
          {!collapsed && <span className="ml-2 font-semibold text-sm">Trading Bot</span>}
          {/* Desktop collapse butonu */}
          <button
            onClick={toggleCollapse}
            className="ml-auto hidden sm:flex shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground transition-colors"
            title={collapsed ? "Genişlet" : "Daralt"}
          >
            <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
          </button>
          {/* Mobil kapat butonu */}
          <button
            onClick={close}
            className="ml-auto sm:hidden shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-2">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={close}
                title={collapsed ? label : undefined}
                className={cn(
                  "flex items-center rounded-md transition-colors",
                  collapsed ? "justify-center px-2 py-2" : "gap-2.5 px-3 py-2",
                  active
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="text-sm">{label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="border-t border-border p-2">
          <div className={cn("flex items-center rounded-md px-3 py-2", collapsed && "justify-center px-2")}>
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
              <User className="h-4 w-4 text-muted-foreground" />
            </div>
            {!collapsed && (
              <>
                <span className="ml-2.5 text-sm font-medium truncate flex-1">{username}</span>
                <button
                  onClick={logout}
                  className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
                  title="Çıkış"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </>
            )}
          </div>
          {collapsed && (
            <button
              onClick={logout}
              title="Çıkış"
              className="mt-1 flex w-full items-center justify-center rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
