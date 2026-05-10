"use client";

import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { Pagination } from "@/components/shared/pagination";
import { SortableHeader } from "@/components/shared/sortable-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import {
  useAddFavorite,
  useFavorites,
  useMarketCoins,
  useRemoveFavorite,
} from "@/hooks/use-market";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatChangePercent, formatPrice, formatVolume } from "@/lib/format";
import type { MarketCoinItem } from "@/types/api";
import {
  Coins,
  Search,
  Star,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type TimeWindow = "1h" | "4h" | "1d";

const WINDOW_LABELS: Record<TimeWindow, string> = {
  "1h": "1s",
  "4h": "4s",
  "1d": "24s",
};

const PAGE_SIZE = 50;

export default function CryptosPage() {
  const router = useRouter();
  const { setPageHeader } = usePageHeader();

  const [window, setWindow] = useState<TimeWindow>("1d");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const { data, isLoading } = useMarketCoins(window);
  const { data: favData } = useFavorites();
  const addFavorite = useAddFavorite();
  const removeFavorite = useRemoveFavorite();

  useEffect(() => {
    setPageHeader("Kriptolar", "Tüm piyasa görünümü — Binance USDT çiftleri");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  // Arama değişince sayfa sıfırla
  useEffect(() => {
    setPage(0);
  }, [search]);

  const favorites = useMemo(() => new Set(favData?.favorites ?? []), [favData]);
  const coins = data?.coins ?? [];

  // Arama filtresi
  const filtered = useMemo(() => {
    if (!search) return coins;
    const q = search.toUpperCase();
    return coins.filter((c) => c.symbol.includes(q));
  }, [coins, search]);

  // Tek useTableSort — tüm filtrelenmiş veri üzerinde sırala
  const { sortedData, sort, toggleSort } = useTableSort(
    filtered,
    "volume_24h",
    "desc",
  );

  // Favorileri üste pin'le (sıralama korunarak)
  const pinned = useMemo(() => {
    const favs = sortedData.filter((c) =>
      favorites.has((c as MarketCoinItem).symbol),
    );
    const rest = sortedData.filter(
      (c) => !favorites.has((c as MarketCoinItem).symbol),
    );
    return [...favs, ...rest];
  }, [sortedData, favorites]);

  // Pagination
  const totalFiltered = pinned.length;
  const paged = pinned.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // İstatistikler
  const rising = coins.filter((c) => c.change_pct > 0).length;
  const falling = coins.filter((c) => c.change_pct < 0).length;

  function toggleFavorite(e: React.MouseEvent, symbol: string) {
    e.stopPropagation();
    if (favorites.has(symbol)) {
      removeFavorite.mutate(symbol);
    } else {
      addFavorite.mutate(symbol);
    }
  }

  const changeLabel = `${WINDOW_LABELS[window]} Değişim`;

  return (
    <div className="space-y-4">
      {/* Özet kartları */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Coins className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-2xl font-bold">{coins.length}</p>
              <p className="text-xs text-muted-foreground">Toplam Coin</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <TrendingUp className="h-5 w-5 text-emerald-500" />
            <div>
              <p className="text-2xl font-bold">{rising}</p>
              <p className="text-xs text-muted-foreground">Yükselen</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <TrendingDown className="h-5 w-5 text-red-500" />
            <div>
              <p className="text-2xl font-bold">{falling}</p>
              <p className="text-xs text-muted-foreground">Düşen</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <Star className="h-5 w-5 text-amber-500" />
            <div>
              <p className="text-2xl font-bold">{favorites.size}</p>
              <p className="text-xs text-muted-foreground">Favori</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Arama + Zaman penceresi + Tablo */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Coin ara... (BTC, ETH, SOL)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex rounded-md border border-border overflow-hidden">
              {(["1h", "4h", "1d"] as TimeWindow[]).map((w) => (
                <Button
                  key={w}
                  variant="ghost"
                  size="sm"
                  onClick={() => setWindow(w)}
                  className={`rounded-none px-3 text-xs ${
                    window === w
                      ? "bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
                      : ""
                  }`}
                >
                  {WINDOW_LABELS[w]}
                </Button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !pinned.length ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              {search ? "Sonuç bulunamadı" : "Piyasa verisi yüklenemedi"}
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8" />
                      <TableHead className="w-10 text-center">#</TableHead>
                      <SortableHeader
                        label="Coin"
                        sortKey="symbol"
                        currentSort={sort}
                        onSort={toggleSort}
                      />
                      <SortableHeader
                        label="Fiyat"
                        sortKey="price"
                        currentSort={sort}
                        onSort={toggleSort}
                      />
                      <SortableHeader
                        label={changeLabel}
                        sortKey="change_pct"
                        currentSort={sort}
                        onSort={toggleSort}
                      />
                      <SortableHeader
                        label="24s Hacim"
                        sortKey="volume_24h"
                        currentSort={sort}
                        onSort={toggleSort}
                        className="hidden sm:table-cell"
                      />
                      <TableHead className="hidden md:table-cell">
                        Sinyal
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paged.map((coin, index) => {
                      const c = coin as MarketCoinItem;
                      const isFav = favorites.has(c.symbol);
                      const rowNum = page * PAGE_SIZE + index + 1;
                      return (
                        <TableRow
                          key={c.symbol}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => router.push(`/pairs/${c.symbol}`)}
                        >
                          <TableCell className="w-8 px-2">
                            <button
                              onClick={(e) => toggleFavorite(e, c.symbol)}
                              className="hover:scale-110 transition-transform"
                            >
                              <Star
                                className={`h-4 w-4 ${isFav ? "fill-amber-500 text-amber-500" : "text-muted-foreground"}`}
                              />
                            </button>
                          </TableCell>
                          <TableCell className="text-center text-xs text-muted-foreground">
                            {rowNum}
                          </TableCell>
                          <TableCell>
                            <div>
                              <span className="font-mono text-xs font-medium">
                                {c.symbol.replace("USDT", "")}
                              </span>
                              <span className="text-[10px] text-muted-foreground ml-1">
                                /USDT
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {formatPrice(c.price)}
                          </TableCell>
                          <TableCell>
                            <span
                              className={`text-xs font-medium ${c.change_pct >= 0 ? "text-emerald-500" : "text-red-500"}`}
                            >
                              {formatChangePercent(c.change_pct)}
                            </span>
                          </TableCell>
                          <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                            {formatVolume(c.volume_24h)}
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            {c.has_signal ? (
                              <div className="flex items-center gap-1">
                                <StatusBadge status={c.signal_side ?? ""} />
                                <ConfidenceBadge
                                  confidence={c.signal_confidence ?? 0}
                                />
                              </div>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                —
                              </span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              <Pagination
                page={page}
                total={totalFiltered}
                limit={PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
