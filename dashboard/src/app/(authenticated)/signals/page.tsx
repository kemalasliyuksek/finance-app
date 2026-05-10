"use client";

import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { Pagination } from "@/components/shared/pagination";
import { SortableHeader } from "@/components/shared/sortable-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
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
import { useApproveSignal, useRejectSignal, useSignals } from "@/hooks/use-signals";
import { useSignalDetail } from "@/hooks/use-signal-detail";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatChangePercent, formatDate, formatDuration, formatPrice, formatUSD } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Circle,
  Clock,
  FileText,
  Package,
  ShieldCheck,
  TrendingUp,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

const statuses = [
  { value: undefined, label: "Tümü" },
  { value: "pending", label: "Bekleyen" },
  { value: "approved", label: "Onaylanan" },
  { value: "executed", label: "Gerçekleşen" },
  { value: "rejected", label: "Reddedilen" },
  { value: "expired", label: "Süre Aşımı" },
  { value: "weak", label: "Zayıf" },
];

const timelineIcons: Record<string, { icon: typeof CheckCircle2; color: string }> = {
  signal_created: { icon: FileText, color: "text-blue-500" },
  approve: { icon: CheckCircle2, color: "text-emerald-500" },
  reject: { icon: XCircle, color: "text-red-500" },
  risk_check_passed: { icon: ShieldCheck, color: "text-emerald-500" },
  order_created: { icon: Package, color: "text-blue-500" },
  order_filled: { icon: TrendingUp, color: "text-emerald-500" },
  trade_opened: { icon: ArrowUpRight, color: "text-emerald-500" },
  execution_failed: { icon: AlertCircle, color: "text-red-500" },
  risk_rejected: { icon: XCircle, color: "text-red-500" },
};

const timelineLabels: Record<string, string> = {
  signal_created: "Sinyal oluşturuldu",
  approve: "Onaylandı",
  reject: "Reddedildi",
  risk_check_passed: "Risk kontrolü geçti",
  order_created: "Emir oluşturuldu",
  order_filled: "Emir dolduruldu",
  trade_opened: "Pozisyon açıldı",
  execution_failed: "Yürütme hatası",
  risk_rejected: "Risk kontrolü reddetti",
};

export default function SignalsPage() {
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("Sinyaller", "Sinyal listesi ve onay yönetimi");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [status, setStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const limit = 20;

  const { sort, toggleSort } = useTableSort([], "created_at", "desc");
  const { data, isLoading } = useSignals({
    status, limit, offset: page * limit,
    sort_by: sort.key, sort_order: sort.direction,
  });
  const approve = useApproveSignal();
  const reject = useRejectSignal();
  const items = data?.items ?? [];
  const { data: detail, isLoading: detailLoading } = useSignalDetail(selectedId);

  return (
    <div className="space-y-4">
      <Tabs
        value={status ?? "all"}
        onValueChange={(v) => {
          setStatus(v === "all" ? undefined : v);
          setPage(0);
        }}
      >
        <TabsList className="flex-wrap h-auto gap-1">
          {statuses.map((s) => (
            <TabsTrigger key={s.value ?? "all"} value={s.value ?? "all"}>
              {s.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{data?.total ?? 0} sinyal</CardTitle>
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
                    <SortableHeader label="Tarih" sortKey="created_at" currentSort={sort} onSort={toggleSort} className="hidden sm:table-cell" />
                    <SortableHeader label="Çift" sortKey="symbol" currentSort={sort} onSort={toggleSort} />
                    <SortableHeader label="Yön" sortKey="side" currentSort={sort} onSort={toggleSort} />
                    <SortableHeader label="Güven" sortKey="confidence" currentSort={sort} onSort={toggleSort} />
                    <TableHead className="hidden sm:table-cell">Giriş</TableHead>
                    <TableHead className="hidden md:table-cell">Stop Loss</TableHead>
                    <TableHead className="hidden md:table-cell">Take Profit</TableHead>
                    <SortableHeader label="Durum" sortKey="status" currentSort={sort} onSort={toggleSort} />
                    <TableHead>İşlem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((signal, index) => (
                    <TableRow
                      key={signal.id}
                      className="cursor-pointer"
                      onClick={() => setSelectedId(signal.id)}
                    >
                      <TableCell className="text-center text-xs text-muted-foreground">{index + 1}</TableCell>
                      <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">{formatDate(signal.created_at)}</TableCell>
                      <TableCell className="font-mono text-xs font-medium">{signal.symbol}</TableCell>
                      <TableCell><StatusBadge status={signal.side} /></TableCell>
                      <TableCell><ConfidenceBadge confidence={signal.confidence} /></TableCell>
                      <TableCell className="hidden sm:table-cell font-mono text-xs">{formatPrice(signal.entry_price)}</TableCell>
                      <TableCell className="hidden md:table-cell font-mono text-xs">{signal.stop_loss ? formatPrice(signal.stop_loss) : "-"}</TableCell>
                      <TableCell className="hidden md:table-cell font-mono text-xs">{signal.take_profit ? formatPrice(signal.take_profit) : "-"}</TableCell>
                      <TableCell><StatusBadge status={signal.status} /></TableCell>
                      <TableCell>
                        {signal.status === "pending" && (
                          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                            <Button
                              size="icon" variant="ghost"
                              className="h-7 w-7 text-emerald-500 hover:text-emerald-400"
                              onClick={() => approve.mutate(signal.id)}
                              disabled={approve.isPending}
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                            <Button
                              size="icon" variant="ghost"
                              className="h-7 w-7 text-red-500 hover:text-red-400"
                              onClick={() => reject.mutate(signal.id)}
                              disabled={reject.isPending}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination page={page} total={data?.total ?? 0} limit={limit} onPageChange={setPage} />
            </>
          )}
        </CardContent>
      </Card>

      {/* Sinyal Detay Sheet */}
      <Sheet open={!!selectedId} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              {detail?.signal && (
                <>
                  <StatusBadge status={detail.signal.side} />
                  <span className="font-mono">{detail.signal.symbol}</span>
                </>
              )}
            </SheetTitle>
          </SheetHeader>

          {detailLoading ? (
            <div className="space-y-4 px-4 pb-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : detail?.signal ? (
            <div className="space-y-6 px-4 pb-6">
              {/* Sinyal Bilgileri */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-muted-foreground">Güven</p>
                  <ConfidenceBadge confidence={detail.signal.confidence} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Strateji</p>
                  <p className="text-sm font-mono">{detail.signal.strategy}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Giriş Fiyatı</p>
                  <p className="text-sm font-mono">{formatPrice(detail.signal.entry_price)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Durum</p>
                  <StatusBadge status={detail.signal.status} />
                </div>
                {detail.signal.stop_loss && (
                  <div>
                    <p className="text-xs text-muted-foreground">Stop Loss</p>
                    <p className="text-sm font-mono text-red-500">{formatPrice(detail.signal.stop_loss)}</p>
                  </div>
                )}
                {detail.signal.take_profit && (
                  <div>
                    <p className="text-xs text-muted-foreground">Take Profit</p>
                    <p className="text-sm font-mono text-emerald-500">{formatPrice(detail.signal.take_profit)}</p>
                  </div>
                )}
              </div>

              <Separator />

              {/* Timeline */}
              <div>
                <h3 className="text-sm font-semibold mb-3">Zaman Çizelgesi</h3>
                <div className="space-y-0">
                  {detail.timeline.map((event, i) => {
                    const config = timelineIcons[event.action] ?? { icon: Circle, color: "text-muted-foreground" };
                    const Icon = config.icon;
                    const label = timelineLabels[event.action] ?? event.action;
                    const isLast = i === detail.timeline.length - 1;

                    return (
                      <div key={i} className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <Icon className={cn("h-4 w-4 shrink-0 mt-0.5", config.color)} />
                          {!isLast && <div className="w-px flex-1 bg-border my-1" />}
                        </div>
                        <div className="pb-4 min-w-0">
                          <p className="text-sm font-medium">{label}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatDate(event.timestamp)}
                            {event.user && event.user !== "system" && ` — ${event.user}`}
                          </p>
                          {event.details && (() => {
                            const d = event.details as Record<string, unknown>;
                            return (
                              <div className="mt-1 text-xs text-muted-foreground">
                                {d.error ? <p className="text-red-500">{String(d.error)}</p> : null}
                                {d.reason ? <p className="text-red-500">{String(d.reason)}</p> : null}
                                {d.fill_price ? <p>Dolum: {formatPrice(Number(d.fill_price))} x {Number(d.fill_qty).toFixed(6)}</p> : null}
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* İlişkili Order */}
              {detail.order && (
                <>
                  <Separator />
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Emir</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Durum</p>
                        <StatusBadge status={detail.order.status} />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Tip</p>
                        <p className="font-mono">{detail.order.order_type}</p>
                      </div>
                      {detail.order.avg_fill_price && (
                        <div>
                          <p className="text-xs text-muted-foreground">Dolum Fiyatı</p>
                          <p className="font-mono">{formatPrice(detail.order.avg_fill_price)}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-muted-foreground">Miktar</p>
                        <p className="font-mono">{Number(detail.order.filled_quantity || detail.order.quantity).toFixed(6)}</p>
                      </div>
                      {detail.order.avg_fill_price && detail.order.filled_quantity > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground">Toplam Tutar</p>
                          <p className="font-mono font-medium">{formatUSD(detail.order.avg_fill_price * (detail.order.filled_quantity || detail.order.quantity))}</p>
                        </div>
                      )}
                      {detail.order.commission > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground">Komisyon</p>
                          <p className="font-mono">{Number(detail.order.commission).toFixed(6)} {detail.order.commission_asset}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}

              {/* İlişkili Trade */}
              {detail.trade && (
                <>
                  <Separator />
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Trade</h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Durum</p>
                        <StatusBadge status={detail.trade.status as string} />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Giriş</p>
                        <p className="font-mono">{formatPrice(Number(detail.trade.entry_price))}</p>
                      </div>
                      {detail.trade.exit_price && (
                        <div>
                          <p className="text-xs text-muted-foreground">Çıkış</p>
                          <p className="font-mono">{formatPrice(Number(detail.trade.exit_price))}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-muted-foreground">Miktar</p>
                        <p className="font-mono">{Number(detail.trade.quantity).toFixed(6)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Toplam Tutar</p>
                        <p className="font-mono font-medium">{formatUSD(Number(detail.trade.entry_price) * Number(detail.trade.quantity))}</p>
                      </div>
                      {detail.trade.realized_pnl != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">PnL</p>
                          <p className={cn(
                            "font-mono font-medium",
                            Number(detail.trade.realized_pnl) >= 0 ? "text-emerald-500" : "text-red-500",
                          )}>
                            {formatUSD(Number(detail.trade.realized_pnl))}
                            {detail.trade.realized_pnl_pct != null && (
                              <span className="text-xs ml-1">({formatChangePercent(detail.trade.realized_pnl_pct)})</span>
                            )}
                          </p>
                        </div>
                      )}
                      {detail.trade.duration_seconds != null && (
                        <div>
                          <p className="text-xs text-muted-foreground">Süre</p>
                          <p className="font-mono">{formatDuration(detail.trade.duration_seconds)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
