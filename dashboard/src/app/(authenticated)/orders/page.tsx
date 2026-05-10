"use client";

import { useEffect, useState } from "react";
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
import { usePageHeader } from "@/contexts/page-header-context";
import { useOrders } from "@/hooks/use-orders";
import { useTableSort } from "@/hooks/use-table-sort";
import { formatDate, formatPrice, formatQuantity, formatUSD } from "@/lib/format";
import type { Order } from "@/types/api";

const LIMIT = 20;

export default function OrdersPage() {
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("Emirler", "Emir geçmişi");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [page, setPage] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const { sort, toggleSort } = useTableSort([], "created_at", "desc");
  const { data, isLoading } = useOrders({
    limit: LIMIT, offset: page * LIMIT,
    sort_by: sort.key, sort_order: sort.direction,
  });
  const items = data?.items ?? [];

  function getTotal(order: Order): number | null {
    const price = order.avg_fill_price ?? order.price;
    const qty = order.filled_quantity || order.quantity;
    if (price && qty) return price * qty;
    return null;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {data?.total ?? 0} emir
          </CardTitle>
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
                    <TableHead className="hidden md:table-cell">Tip</TableHead>
                    <TableHead className="hidden sm:table-cell">Tutar</TableHead>
                    <TableHead className="hidden md:table-cell">Dolum Fiyatı</TableHead>
                    <SortableHeader label="Durum" sortKey="status" currentSort={sort} onSort={toggleSort} />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((order, index) => {
                    const total = getTotal(order);
                    return (
                      <TableRow
                        key={order.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => setSelectedOrder(order)}
                      >
                        <TableCell className="text-center text-xs text-muted-foreground">
                          {page * LIMIT + index + 1}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                          {formatDate(order.created_at)}
                        </TableCell>
                        <TableCell className="font-mono text-xs font-medium">
                          {order.symbol}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={order.side} />
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-xs">
                          {order.order_type}
                        </TableCell>
                        <TableCell className="hidden sm:table-cell font-mono text-xs">
                          {total ? formatUSD(total) : "-"}
                        </TableCell>
                        <TableCell className="hidden md:table-cell font-mono text-xs">
                          {order.avg_fill_price ? formatPrice(order.avg_fill_price) : "-"}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={order.status} />
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

      {/* Emir Detay Sheet */}
      <Sheet open={!!selectedOrder} onOpenChange={(open) => !open && setSelectedOrder(null)}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="font-mono">
              {selectedOrder?.symbol} — Emir Detayı
            </SheetTitle>
          </SheetHeader>
          {selectedOrder && (
            <div className="space-y-4 px-4 pb-6">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Yön</p>
                  <StatusBadge status={selectedOrder.side} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Durum</p>
                  <StatusBadge status={selectedOrder.status} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Tip</p>
                  <p className="font-mono">{selectedOrder.order_type}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Tarih</p>
                  <p className="text-xs">{formatDate(selectedOrder.created_at)}</p>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Miktar</p>
                  <p className="font-mono">{formatQuantity(selectedOrder.quantity)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Dolum Miktarı</p>
                  <p className="font-mono">{formatQuantity(selectedOrder.filled_quantity)}</p>
                </div>
                {selectedOrder.price && (
                  <div>
                    <p className="text-xs text-muted-foreground">Fiyat</p>
                    <p className="font-mono">{formatPrice(selectedOrder.price)}</p>
                  </div>
                )}
                {selectedOrder.avg_fill_price && (
                  <div>
                    <p className="text-xs text-muted-foreground">Dolum Fiyatı</p>
                    <p className="font-mono">{formatPrice(selectedOrder.avg_fill_price)}</p>
                  </div>
                )}
                {getTotal(selectedOrder) && (
                  <div>
                    <p className="text-xs text-muted-foreground">Toplam Tutar</p>
                    <p className="font-mono font-medium">{formatUSD(getTotal(selectedOrder)!)}</p>
                  </div>
                )}
                {selectedOrder.commission > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground">Komisyon</p>
                    <p className="font-mono">{Number(selectedOrder.commission).toFixed(6)} {selectedOrder.commission_asset}</p>
                  </div>
                )}
              </div>

              {selectedOrder.error_message && (
                <>
                  <Separator />
                  <div>
                    <p className="text-xs text-muted-foreground">Hata</p>
                    <p className="text-sm text-red-500">{selectedOrder.error_message}</p>
                  </div>
                </>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
