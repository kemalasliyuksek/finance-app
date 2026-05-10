"use client";

import { Pagination } from "@/components/shared/pagination";
import { SortableHeader } from "@/components/shared/sortable-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePageHeader } from "@/contexts/page-header-context";
import { useMarketCoins } from "@/hooks/use-market";
import { useTradeStats, useTrades } from "@/hooks/use-trades";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatChangePercent, formatDate, formatDuration, formatPercent, formatPrice, formatUSD } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Trade } from "@/types/api";
import { useEffect, useMemo, useState } from "react";

const LIMIT = 20;

function LiveDuration({ openedAt }: { openedAt: string }) {
  const [elapsed, setElapsed] = useState("");

  useEffect(() => {
    function calc() {
      const diff = Math.floor((Date.now() - new Date(openedAt).getTime()) / 1000);
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      if (h > 0) setElapsed(`${h}sa ${m}dk`);
      else if (m > 0) setElapsed(`${m}dk ${s}s`);
      else setElapsed(`${s}s`);
    }
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, [openedAt]);

  return <span>{elapsed}</span>;
}

function TradeDuration({ trade }: { trade: Trade }) {
  if (trade.status === "open") {
    return <LiveDuration openedAt={trade.opened_at} />;
  }
  return <span>{formatDuration(trade.duration_seconds)}</span>;
}

export default function TradesPage() {
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("İşlemler", "İşlem geçmişi ve performans");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [status, setStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(0);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const { sort, toggleSort } = useTableSort([], "opened_at", "desc");
  const { data, isLoading } = useTrades({
    status, limit: LIMIT, offset: page * LIMIT,
    sort_by: sort.key, sort_order: sort.direction,
  });
  const { data: stats } = useTradeStats();
  const { data: marketData } = useMarketCoins();
  const items = data?.items ?? [];

  const priceMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of marketData?.coins ?? []) map.set(c.symbol, c.price);
    return map;
  }, [marketData]);

  function getLivePnl(trade: Trade) {
    if (trade.status !== "open") return null;
    const currentPrice = priceMap.get(trade.symbol);
    if (!currentPrice) return null;
    const ep = Number(trade.entry_price);
    const qty = Number(trade.quantity);
    const pnl = trade.side === "BUY" ? (currentPrice - ep) * qty : (ep - currentPrice) * qty;
    const pnlPct = ((currentPrice - ep) / ep) * 100 * (trade.side === "BUY" ? 1 : -1);
    return { pnl, pnlPct, currentPrice };
  }

  return (
    <div className="space-y-4">
      {/* İstatistikler */}
      {stats && (
        <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Toplam İşlem</p>
              <p className="text-xl font-bold font-mono">{stats.total_trades}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Kazanma Oranı</p>
              <p className="text-xl font-bold font-mono">
                {formatPercent(stats.win_rate)}
              </p>
              <p className="text-xs text-muted-foreground">
                {stats.winning_trades}K / {stats.losing_trades}Z
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Toplam Kâr/Zarar</p>
              <p
                className={cn(
                  "text-xl font-bold font-mono",
                  Number(stats.total_pnl) >= 0 ? "text-emerald-500" : "text-red-500",
                )}
              >
                {formatUSD(stats.total_pnl)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Ort. Kâr/Zarar</p>
              <p
                className={cn(
                  "text-xl font-bold font-mono",
                  Number(stats.avg_pnl) >= 0 ? "text-emerald-500" : "text-red-500",
                )}
              >
                {formatUSD(stats.avg_pnl)}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs
        value={status ?? "all"}
        onValueChange={(v) => { setStatus(v === "all" ? undefined : v); setPage(0); }}
      >
        <TabsList>
          <TabsTrigger value="all">Tümü</TabsTrigger>
          <TabsTrigger value="open">Açık</TabsTrigger>
          <TabsTrigger value="closed">Kapalı</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{data?.total ?? 0} işlem</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10 text-center">#</TableHead>
                    <SortableHeader label="Tarih" sortKey="opened_at" currentSort={sort} onSort={toggleSort} className="hidden sm:table-cell" />
                    <SortableHeader label="Çift" sortKey="symbol" currentSort={sort} onSort={toggleSort} />
                    <TableHead>Yön</TableHead>
                    <TableHead className="hidden sm:table-cell">Tutar</TableHead>
                    <TableHead className="hidden md:table-cell">Giriş</TableHead>
                    <TableHead className="hidden md:table-cell">Çıkış/Güncel</TableHead>
                    <SortableHeader label="Kâr/Zarar" sortKey="realized_pnl" currentSort={sort} onSort={toggleSort} />
                    <SortableHeader label="Kâr/Zarar %" sortKey="realized_pnl_pct" currentSort={sort} onSort={toggleSort} className="hidden sm:table-cell" />
                    <TableHead className="hidden md:table-cell">Süre</TableHead>
                    <SortableHeader label="Durum" sortKey="status" currentSort={sort} onSort={toggleSort} />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((trade, index) => {
                    const live = getLivePnl(trade);
                    const pnl = live ? live.pnl : trade.realized_pnl;
                    const pnlPct = live ? live.pnlPct : trade.realized_pnl_pct;
                    const hasPnl = pnl != null;
                    const pnlPositive = (pnl ?? 0) >= 0;
                    const total = Number(trade.entry_price) * Number(trade.quantity);
                    return (
                      <TableRow
                        key={trade.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => setSelectedTrade(trade)}
                      >
                        <TableCell className="text-center text-xs text-muted-foreground">
                          {page * LIMIT + index + 1}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                          {formatDate(trade.opened_at)}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-medium">
                          {trade.symbol}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={trade.side} />
                        </TableCell>
                        <TableCell className="hidden sm:table-cell font-mono text-xs">
                          {formatUSD(total)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell font-mono text-xs">
                          {formatPrice(trade.entry_price)}
                        </TableCell>
                        <TableCell className="hidden md:table-cell font-mono text-xs">
                          {live ? (
                            <span className={pnlPositive ? "text-emerald-500" : "text-red-500"}>
                              {formatPrice(live.currentPrice)}
                            </span>
                          ) : trade.exit_price ? formatPrice(trade.exit_price) : "-"}
                        </TableCell>
                        <TableCell
                          className={cn(
                            "font-mono text-xs font-medium",
                            hasPnl ? (pnlPositive ? "text-emerald-500" : "text-red-500") : "",
                          )}
                        >
                          {hasPnl ? formatUSD(pnl) : "-"}
                        </TableCell>
                        <TableCell
                          className={cn(
                            "hidden sm:table-cell font-mono text-xs",
                            hasPnl ? (pnlPositive ? "text-emerald-500" : "text-red-500") : "",
                          )}
                        >
                          {pnlPct != null ? formatChangePercent(pnlPct) : "-"}
                        </TableCell>
                        <TableCell className="hidden md:table-cell font-mono text-xs text-muted-foreground">
                          <TradeDuration trade={trade} />
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={trade.status} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              <Pagination
                page={page}
                total={data?.total ?? 0}
                limit={LIMIT}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* İşlem Detay */}
      <Sheet open={!!selectedTrade} onOpenChange={(open) => !open && setSelectedTrade(null)}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-mono">
              {selectedTrade?.symbol} — İşlem Detayı
            </SheetTitle>
          </SheetHeader>
          {selectedTrade && (() => {
            const t = selectedTrade;
            const total = Number(t.entry_price) * Number(t.quantity);
            const live = getLivePnl(t);
            const pnl = live ? live.pnl : t.realized_pnl;
            const pnlPct = live ? live.pnlPct : t.realized_pnl_pct;
            const hasPnl = pnl != null;
            const pnlPositive = (pnl ?? 0) >= 0;
            return (
              <div className="space-y-4 px-4 pb-6">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Yön</p>
                    <StatusBadge status={t.side} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Durum</p>
                    <StatusBadge status={t.status} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Açılış</p>
                    <p className="text-xs">{formatDate(t.opened_at)}</p>
                  </div>
                  {t.closed_at ? (
                    <div>
                      <p className="text-xs text-muted-foreground">Kapanış</p>
                      <p className="text-xs">{formatDate(t.closed_at)}</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs text-muted-foreground">Süre</p>
                      <p className="font-mono"><LiveDuration openedAt={t.opened_at} /></p>
                    </div>
                  )}
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Giriş Fiyatı</p>
                    <p className="font-mono">{formatPrice(t.entry_price)}</p>
                  </div>
                  {t.exit_price ? (
                    <div>
                      <p className="text-xs text-muted-foreground">Çıkış Fiyatı</p>
                      <p className="font-mono">{formatPrice(t.exit_price)}</p>
                    </div>
                  ) : live ? (
                    <div>
                      <p className="text-xs text-muted-foreground">Güncel Fiyat</p>
                      <p className={cn("font-mono font-medium", pnlPositive ? "text-emerald-500" : "text-red-500")}>
                        {formatPrice(live.currentPrice)}
                      </p>
                    </div>
                  ) : null}
                  <div>
                    <p className="text-xs text-muted-foreground">Miktar</p>
                    <p className="font-mono">{Number(t.quantity).toFixed(6)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Toplam Tutar</p>
                    <p className="font-mono font-medium">{formatUSD(total)}</p>
                  </div>
                </div>

                {hasPnl && (
                  <>
                    <Separator />
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">{live ? "Anlık Kâr/Zarar" : "Kâr/Zarar"}</p>
                        <p className={cn(
                          "font-mono font-medium",
                          pnlPositive ? "text-emerald-500" : "text-red-500",
                        )}>
                          {formatUSD(pnl)}
                        </p>
                      </div>
                      {pnlPct != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">{live ? "Anlık Kâr/Zarar %" : "Kâr/Zarar %"}</p>
                          <p className={cn(
                            "font-mono font-medium",
                            pnlPositive ? "text-emerald-500" : "text-red-500",
                          )}>
                            {formatChangePercent(pnlPct)}
                          </p>
                        </div>
                      )}
                      {t.total_commission > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground">Komisyon</p>
                          <p className="font-mono">{formatUSD(t.total_commission)}</p>
                        </div>
                      )}
                      {t.duration_seconds != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">Süre</p>
                          <p className="font-mono">{formatDuration(t.duration_seconds)}</p>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {(t.stop_loss != null || t.take_profit != null) && (
                  <>
                    <Separator />
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      {t.stop_loss != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">Stop Loss</p>
                          <p className="font-mono text-red-500">{formatPrice(Number(t.stop_loss))}</p>
                        </div>
                      )}
                      {t.take_profit != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">Take Profit</p>
                          <p className="font-mono text-emerald-500">{formatPrice(Number(t.take_profit))}</p>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })()}
        </SheetContent>
      </Sheet>
    </div>
  );
}
