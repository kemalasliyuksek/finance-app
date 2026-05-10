"use client";

import { usePageHeader } from "@/contexts/page-header-context";
import { useSidebar } from "@/contexts/sidebar-context";
import { useDashboard } from "@/hooks/use-dashboard";
import { useWebSocket } from "@/providers/websocket-provider";
import { cn } from "@/lib/utils";
import { Menu } from "lucide-react";

export function Topbar() {
  const { title, description } = usePageHeader();
  const { isConnected } = useWebSocket();
  const { toggle } = useSidebar();
  const { data: summary } = useDashboard();

  const appMode = summary?.app_mode;
  const tradingMode = summary?.trading_mode;

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {/* Mobil hamburger */}
        <button
          onClick={toggle}
          className="sm:hidden shrink-0 rounded-md p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          {title && <h1 className="text-lg font-semibold leading-tight truncate">{title}</h1>}
          {description && (
            <p className="text-xs text-muted-foreground truncate">{description}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 ml-4 shrink-0">
        {/* Mod badge'leri */}
        {appMode && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              appMode === "live"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
                : "border-amber-500/30 bg-amber-500/10 text-amber-500",
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", appMode === "live" ? "bg-emerald-500" : "bg-amber-500")} />
            {appMode}
          </span>
        )}
        {tradingMode && (
          <span
            className={cn(
              "hidden sm:inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium",
              tradingMode === "full_auto"
                ? "border-blue-500/30 bg-blue-500/10 text-blue-500"
                : "border-zinc-500/30 bg-zinc-500/10 text-zinc-400",
            )}
          >
            {tradingMode === "full_auto" ? "Otomatik" : "Yarı Otomatik"}
          </span>
        )}

        {/* Bağlantı durumu badge */}
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-medium",
            isConnected
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
              : "border-red-500/30 bg-red-500/10 text-red-500",
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", isConnected ? "bg-emerald-500" : "bg-red-500")} />
          <span className="hidden sm:inline">{isConnected ? "Canlı" : "Bağlantı yok"}</span>
        </span>
      </div>
    </header>
  );
}
