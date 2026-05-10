"use client";

import { SortableHeader } from "@/components/shared/sortable-header";
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
import { usePageHeader } from "@/contexts/page-header-context";
import { useBinanceAccount } from "@/hooks/use-binance-account";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatAssetValue } from "@/lib/format";
import { Landmark } from "lucide-react";
import { useEffect } from "react";

export default function BinancePage() {
  const { setPageHeader } = usePageHeader();
  const { data: account, isLoading, isError } = useBinanceAccount();
  const { sortedData, sort, toggleSort } = useTableSort(account?.balances ?? [], "total", "desc");

  useEffect(() => {
    const desc = account
      ? `${account.account_type} — ${account.can_trade ? "İşlem açık" : "İşlem kapalı"}`
      : "Hesap bilgileri yükleniyor...";
    setPageHeader("Binance Hesabı", desc);
    return () => setPageHeader("", "");
  }, [setPageHeader, account]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Landmark className="h-4 w-4" />
            Varlıklar
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : isError ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Binance API bağlantısı kurulamadı. API key ayarlarını kontrol edin.
            </p>
          ) : !account?.balances?.length ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Hesapta varlık bulunamadı.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10 text-center">#</TableHead>
                  <SortableHeader label="Varlık" sortKey="asset" currentSort={sort} onSort={toggleSort} />
                  <SortableHeader label="Serbest" sortKey="free" currentSort={sort} onSort={toggleSort} className="text-right" />
                  <TableHead className="text-right">Kilitli</TableHead>
                  <SortableHeader label="Toplam" sortKey="total" currentSort={sort} onSort={toggleSort} className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((b, index) => (
                  <TableRow key={b.asset as string}>
                    <TableCell className="text-center text-xs text-muted-foreground">
                      {index + 1}
                    </TableCell>
                    <TableCell className="font-mono font-medium">{b.asset as string}</TableCell>
                    <TableCell className="font-mono text-xs text-right">
                      {formatAssetValue(b.asset as string, b.free as number)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-right">
                      {formatAssetValue(b.asset as string, b.locked as number)}
                    </TableCell>
                    <TableCell className="font-mono text-xs font-medium text-right">
                      {formatAssetValue(b.asset as string, b.total as number)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
