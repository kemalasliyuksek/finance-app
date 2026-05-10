"use client";

import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { SortableHeader } from "@/components/shared/sortable-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
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
import { usePageHeader } from "@/contexts/page-header-context";
import { useScreenerResults, useScreenerStatus } from "@/hooks/use-screener";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatPrice, formatVolume } from "@/lib/format";
import type { ScreenerResultItem } from "@/types/api";
import { Activity, Search, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

export default function ScreenerPage() {
  const { setPageHeader } = usePageHeader();
  const { data, isLoading } = useScreenerResults();
  const { data: status } = useScreenerStatus();
  const { sortedData, sort, toggleSort } = useTableSort(data?.results ?? [], "confidence", "desc");
  const [selected, setSelected] = useState<ScreenerResultItem | null>(null);

  useEffect(() => {
    const scanInfo = status?.last_scan_at
      ? `Son tarama: ${new Date(status.last_scan_at).toLocaleTimeString("tr-TR")}${status.cycle_duration_seconds != null ? ` (${status.cycle_duration_seconds.toFixed(1)}s)` : ""}`
      : "Otomatik piyasa tarama sonuçları";
    setPageHeader("Piyasa Tarama", scanInfo);
    return () => setPageHeader("", "");
  }, [setPageHeader, status?.last_scan_at, status?.cycle_duration_seconds]);

  return (
    <div className="space-y-4">
      {/* Durum kartları */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Search className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-2xl font-bold">
                {status?.total_pairs_scanned ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Taranan Coin</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-2xl font-bold">
                {status?.candidates_analyzed ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Analiz Edilen</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Activity className="h-5 w-5 text-emerald-500" />
            <div>
              <p className="text-2xl font-bold">
                {status?.active_pairs?.length ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Aktif Coin</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Activity className="h-5 w-5 text-amber-500" />
            <div>
              <p className="text-2xl font-bold">
                {status?.dynamic_pairs?.length ?? 0}
              </p>
              <p className="text-xs text-muted-foreground">Dinamik Coin</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sonuç tablosu */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {data?.results?.length ?? 0} aday ({data?.total_scanned ?? 0} taranan)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !data?.results?.length ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Henüz tarama sonucu yok. İlk tarama ~30 saniye sonra başlar, her 5 dakikada güncellenir.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10 text-center">#</TableHead>
                  <SortableHeader label="Coin" sortKey="symbol" currentSort={sort} onSort={toggleSort} />
                  <TableHead className="hidden sm:table-cell">Fiyat</TableHead>
                  <SortableHeader label="24s Değişim" sortKey="change_24h" currentSort={sort} onSort={toggleSort} />
                  <SortableHeader label="24s Hacim" sortKey="volume_24h" currentSort={sort} onSort={toggleSort} className="hidden sm:table-cell" />
                  <TableHead>Yön</TableHead>
                  <SortableHeader label="Güven" sortKey="confidence" currentSort={sort} onSort={toggleSort} />
                  <TableHead className="hidden md:table-cell">TA Özet</TableHead>
                  <TableHead>Durum</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((item, index) => (
                  <TableRow
                    key={item.symbol as string}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => setSelected(item as ScreenerResultItem)}
                  >
                    <TableCell className="text-center text-xs text-muted-foreground">
                      {index + 1}
                    </TableCell>
                    <TableCell className="font-mono text-xs font-medium">
                      {item.symbol as string}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell font-mono text-xs">
                      {formatPrice(item.price as number)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          (item.change_24h as number) >= 0
                            ? "text-emerald-500"
                            : "text-red-500"
                        }
                      >
                        {(item.change_24h as number) >= 0 ? "+" : ""}
                        {(item.change_24h as number).toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                      {formatVolume(item.volume_24h as number)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={item.side as string} />
                    </TableCell>
                    <TableCell>
                      <ConfidenceBadge confidence={item.confidence as number} />
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-xs text-muted-foreground">
                      {(item.ta_summary as Record<string, unknown>)?.ema_trend === "up" ? "EMA+" : "EMA-"}{" "}
                      RSI:{typeof (item.ta_summary as Record<string, unknown>)?.rsi === "number"
                        ? Math.round((item.ta_summary as Record<string, unknown>).rsi as number)
                        : "-"}{" "}
                      {(item.ta_summary as Record<string, unknown>)?.volume_spike ? "VOL!" : ""}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {item.is_active && (
                          <Badge
                            variant="outline"
                            className="border-emerald-500/50 text-emerald-500 text-[10px]"
                          >
                            Aktif
                          </Badge>
                        )}
                        {item.is_volume_top && (
                          <Badge
                            variant="outline"
                            className="border-amber-500/50 text-amber-500 text-[10px]"
                          >
                            Top Hacim
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Tarama Detay Sheet */}
      <Sheet open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-mono">
              {selected?.symbol} — Tarama Detayı
            </SheetTitle>
          </SheetHeader>
          {selected && (() => {
            const s = selected;
            const ta = (s.ta_summary ?? {}) as Record<string, unknown>;
            return (
              <div className="space-y-4 px-4 pb-6">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Yön</p>
                    <StatusBadge status={s.side} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Güven</p>
                    <ConfidenceBadge confidence={s.confidence} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Fiyat</p>
                    <p className="font-mono">{formatPrice(s.price)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">24s Değişim</p>
                    <p className={`font-mono font-medium ${s.change_24h >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                      {s.change_24h >= 0 ? "+" : ""}{s.change_24h.toFixed(2)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">24s Hacim</p>
                    <p className="font-mono">{formatVolume(s.volume_24h)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Tarama Skoru</p>
                    <p className="font-mono">{(s.scan_score * 100).toFixed(1)}%</p>
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="text-sm font-semibold mb-2">Teknik Analiz</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">EMA Trend</p>
                      <p className="font-mono">{ta.ema_trend === "up" ? "Yukarı" : ta.ema_trend === "down" ? "Aşağı" : "-"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">EMA Crossover</p>
                      <p className="font-mono">{ta.ema_crossover === "bullish" ? "Boğa" : ta.ema_crossover === "bearish" ? "Ayı" : "-"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">RSI</p>
                      <p className="font-mono">{typeof ta.rsi === "number" ? Math.round(ta.rsi as number) : "-"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">RSI Bölge</p>
                      <p className="font-mono">{ta.rsi_zone === "overbought" ? "Aşırı Alım" : ta.rsi_zone === "oversold" ? "Aşırı Satım" : "Nötr"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">BB Pozisyon</p>
                      <p className="font-mono">{ta.bb_position === "above_upper" ? "Üst Band Üstü" : ta.bb_position === "below_lower" ? "Alt Band Altı" : "Band İçi"}</p>
                    </div>
                    {ta.bb_squeeze != null && (
                      <div>
                        <p className="text-xs text-muted-foreground">BB Squeeze</p>
                        <p className={`font-mono font-medium ${ta.bb_squeeze ? "text-amber-500" : ""}`}>
                          {ta.bb_squeeze ? "Sıkışma Var" : "Yok"}
                        </p>
                      </div>
                    )}
                    <div>
                      <p className="text-xs text-muted-foreground">MACD Crossover</p>
                      <p className="font-mono">{ta.macd_crossover === "bullish" ? "Boğa" : ta.macd_crossover === "bearish" ? "Ayı" : "-"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Hacim Spike</p>
                      <p className={`font-mono font-medium ${ta.volume_spike ? "text-amber-500" : ""}`}>
                        {ta.volume_spike ? "Evet" : "Hayır"}
                        {typeof ta.volume_ratio === "number" ? ` (${(ta.volume_ratio as number).toFixed(1)}x)` : ""}
                      </p>
                    </div>
                    {typeof ta.volume_intensity === "number" && (ta.volume_intensity as number) > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground">Hacim Yoğunluğu</p>
                        <p className="font-mono">{((ta.volume_intensity as number) * 100).toFixed(0)}%</p>
                      </div>
                    )}
                    {typeof ta.atr_pct === "number" && (
                      <div>
                        <p className="text-xs text-muted-foreground">ATR %</p>
                        <p className="font-mono">{(ta.atr_pct as number).toFixed(2)}%</p>
                      </div>
                    )}
                  </div>
                </div>

                <Separator />

                <div className="flex gap-2">
                  {s.is_active && (
                    <Badge variant="outline" className="border-emerald-500/50 text-emerald-500">
                      Aktif Takipte
                    </Badge>
                  )}
                  {s.is_volume_top && (
                    <Badge variant="outline" className="border-amber-500/50 text-amber-500">
                      Top Hacim
                    </Badge>
                  )}
                  {!s.is_active && !s.is_volume_top && (
                    <Badge variant="outline" className="text-muted-foreground">
                      Aday
                    </Badge>
                  )}
                </div>
              </div>
            );
          })()}
        </SheetContent>
      </Sheet>
    </div>
  );
}
