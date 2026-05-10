"use client";

import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDashboard } from "@/hooks/use-dashboard";
import { useMarketCoins } from "@/hooks/use-market";
import { useOpenTrades } from "@/hooks/use-trades";
import {
  formatChangePercent,
  formatDate,
  formatPercent,
  formatPrice,
  formatUSD,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { usePageHeader } from "@/contexts/page-header-context";
import type { Trade } from "@/types/api";
import { Activity, BarChart3, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function LiveDuration({ openedAt }: { openedAt: string }) {
  const [elapsed, setElapsed] = useState("");
  useEffect(() => {
    function calc() {
      const diff = Math.floor(
        (Date.now() - new Date(openedAt).getTime()) / 1000,
      );
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      if (h > 0) setElapsed(`${h}sa ${m}dk`);
      else setElapsed(`${m}dk`);
    }
    calc();
    const id = setInterval(calc, 60000);
    return () => clearInterval(id);
  }, [openedAt]);
  return <span>{elapsed}</span>;
}

export default function DashboardPage() {
  const { setPageHeader } = usePageHeader();
  const { data: summary, isLoading } = useDashboard();
  const { data: openTrades } = useOpenTrades();
  const { data: marketData } = useMarketCoins();

  useEffect(() => {
    const mode = summary?.app_mode?.toUpperCase() ?? "";
    const trading =
      summary?.trading_mode === "semi_auto" ? "Yarı Otomatik" : "Tam Otomatik";
    setPageHeader("Dashboard", mode ? `${mode} — ${trading}` : "Genel bakış");
    return () => setPageHeader("", "");
  }, [setPageHeader, summary?.app_mode, summary?.trading_mode]);

  // Canlı fiyat haritası: symbol → price
  const priceMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of marketData?.coins ?? []) {
      map.set(c.symbol, c.price);
    }
    return map;
  }, [marketData]);

  function getUnrealizedPnl(trade: Trade) {
    const currentPrice = priceMap.get(trade.symbol);
    if (!currentPrice) return null;
    const entry = Number(trade.entry_price);
    const qty = Number(trade.quantity);
    const pnl =
      trade.side === "BUY"
        ? (currentPrice - entry) * qty
        : (entry - currentPrice) * qty;
    const pnlPct = ((currentPrice - entry) / entry) * 100 * (trade.side === "BUY" ? 1 : -1);
    return { pnl, pnlPct, currentPrice };
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  const pnlPositive = (summary?.today_pnl ?? 0) >= 0;
  const unrealizedPositive = (summary?.unrealized_pnl ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Toplam Bakiye
            </CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {formatUSD(summary?.total_balance_usdt)}
            </div>
            <p className="text-xs text-muted-foreground">
              Serbest: {formatUSD(summary?.free_balance_usdt)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Anlık Kâr/Zarar
            </CardTitle>
            {unrealizedPositive ? (
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                "text-2xl font-bold font-mono",
                unrealizedPositive ? "text-emerald-500" : "text-red-500",
              )}
            >
              {formatUSD(summary?.unrealized_pnl)}
            </div>
            <p className="text-xs text-muted-foreground">
              Açık Pozisyon: {summary?.open_positions ?? 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Günlük Kâr/Zarar
            </CardTitle>
            {pnlPositive ? (
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                "text-2xl font-bold font-mono",
                pnlPositive ? "text-emerald-500" : "text-red-500",
              )}
            >
              {formatUSD(summary?.today_pnl)}
            </div>
            <p className="text-xs text-muted-foreground">
              Bugün: {summary?.today_trades_count ?? 0} işlem
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Kazanma Oranı
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">
              {formatPercent(summary?.win_rate)}
            </div>
            <p className="text-xs text-muted-foreground">
              {summary?.active_pairs?.length ?? 0} aktif çift
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Signals & Open Trades */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Son Sinyaller
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary?.recent_signals?.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 text-center">#</TableHead>
                    <TableHead>Çift</TableHead>
                    <TableHead>Yön</TableHead>
                    <TableHead>Güven</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead className="hidden sm:table-cell">
                      Tarih
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.recent_signals.map((signal, index) => (
                    <TableRow key={signal.id}>
                      <TableCell className="text-center text-xs text-muted-foreground">
                        {index + 1}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {signal.symbol}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={signal.side} />
                      </TableCell>
                      <TableCell>
                        <ConfidenceBadge confidence={signal.confidence} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={signal.status} />
                      </TableCell>
                      <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                        {formatDate(signal.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center">
                Henüz sinyal yok
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Açık Pozisyonlar
            </CardTitle>
          </CardHeader>
          <CardContent>
            {openTrades?.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 text-center">#</TableHead>
                    <TableHead>Çift</TableHead>
                    <TableHead>Yön</TableHead>
                    <TableHead className="hidden sm:table-cell">
                      Giriş
                    </TableHead>
                    <TableHead className="hidden sm:table-cell">
                      Güncel
                    </TableHead>
                    <TableHead>Tutar</TableHead>
                    <TableHead>K/Z</TableHead>
                    <TableHead className="hidden md:table-cell">Süre</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {openTrades.map((trade, index) => {
                    const live = getUnrealizedPnl(trade);
                    const pnlPos = live ? live.pnl >= 0 : true;
                    return (
                      <TableRow key={trade.id}>
                        <TableCell className="text-center text-xs text-muted-foreground">
                          {index + 1}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-medium">
                          {trade.symbol}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={trade.side} />
                        </TableCell>
                        <TableCell className="hidden sm:table-cell font-mono text-xs">
                          {formatPrice(trade.entry_price)}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell font-mono text-xs">
                          {live ? (
                            <span className={pnlPos ? "text-emerald-500" : "text-red-500"}>
                              {formatPrice(live.currentPrice)}
                            </span>
                          ) : "-"}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {formatUSD(
                            Number(trade.entry_price) * Number(trade.quantity),
                          )}
                        </TableCell>
                        <TableCell>
                          {live ? (
                            <div>
                              <span
                                className={cn(
                                  "font-mono text-xs font-medium",
                                  pnlPos ? "text-emerald-500" : "text-red-500",
                                )}
                              >
                                {formatUSD(live.pnl)}
                              </span>
                              <span
                                className={cn(
                                  "font-mono text-[10px] ml-1",
                                  pnlPos ? "text-emerald-500" : "text-red-500",
                                )}
                              >
                                ({formatChangePercent(live.pnlPct)})
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-xs text-muted-foreground">
                          <LiveDuration openedAt={trade.opened_at} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center">
                Açık pozisyon yok
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
