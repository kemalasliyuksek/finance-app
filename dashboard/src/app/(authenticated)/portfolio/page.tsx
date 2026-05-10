"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePortfolioCurrent, usePortfolioHistory } from "@/hooks/use-portfolio";
import { usePageHeader } from "@/contexts/page-header-context";
import { formatUSD } from "@/lib/format";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format } from "date-fns";
import { tr } from "date-fns/locale";

export default function PortfolioPage() {
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("Portföy", "Bakiye geçmişi ve varlık dağılımı");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [range, setRange] = useState("7d");
  const { data: current, isLoading: loadingCurrent } = usePortfolioCurrent();
  const { data: history, isLoading: loadingHistory } = usePortfolioHistory(range);

  const chartData = (history ?? []).map((s) => ({
    date: format(new Date(s.snapshot_at), "dd.MM HH:mm", { locale: tr }),
    balance: Number(s.total_balance_usdt),
    unrealized: Number(s.unrealized_pnl),
  }));

  const breakdown = current?.asset_breakdown
    ? Object.entries(current.asset_breakdown)
        .filter(([, v]) => Number(v) > 0)
        .sort(([, a], [, b]) => Number(b) - Number(a))
    : [];

  return (
    <div className="space-y-4">
      {/* Current Balance */}
      {loadingCurrent ? (
        <Skeleton className="h-32" />
      ) : current ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Toplam Bakiye</p>
              <p className="text-2xl font-bold font-mono">
                {formatUSD(current.total_balance_usdt)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Serbest</p>
              <p className="text-2xl font-bold font-mono">
                {formatUSD(current.free_balance_usdt)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">Kilitli</p>
              <p className="text-2xl font-bold font-mono">
                {formatUSD(current.locked_balance_usdt)}
              </p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Portföy verisi yok</p>
      )}

      {/* Balance Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Bakiye Geçmişi</CardTitle>
          <Tabs value={range} onValueChange={setRange}>
            <TabsList className="h-8">
              <TabsTrigger value="24h" className="text-xs px-2">
                24s
              </TabsTrigger>
              <TabsTrigger value="7d" className="text-xs px-2">
                7g
              </TabsTrigger>
              <TabsTrigger value="30d" className="text-xs px-2">
                30g
              </TabsTrigger>
              <TabsTrigger value="all" className="text-xs px-2">
                Tümü
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          {loadingHistory ? (
            <Skeleton className="h-64" />
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="balanceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="date"
                  stroke="#666"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  stroke="#666"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "6px",
                    fontSize: 12,
                  }}
                  formatter={(value) => [formatUSD(Number(value ?? 0)), "Bakiye"]}
                />
                <Area
                  type="monotone"
                  dataKey="balance"
                  stroke="#3b82f6"
                  fill="url(#balanceGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground py-16 text-center">
              Bu aralıkta veri yok
            </p>
          )}
        </CardContent>
      </Card>

      {/* Asset Breakdown */}
      {breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Varlık Dağılımı</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {breakdown.map(([asset, amount]) => (
                <div
                  key={asset}
                  className="flex items-center justify-between py-1"
                >
                  <span className="text-sm font-medium">{asset}</span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {Number(amount).toFixed(6)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
