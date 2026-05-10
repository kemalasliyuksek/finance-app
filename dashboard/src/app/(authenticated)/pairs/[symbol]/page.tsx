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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCandles } from "@/hooks/use-candles";
import { useSignals } from "@/hooks/use-signals";
import { formatDate, formatPrice, formatUSD } from "@/lib/format";
import api from "@/lib/api-client";
import type { SentimentData } from "@/types/api";
import { useQuery } from "@tanstack/react-query";
import { usePageHeader } from "@/contexts/page-header-context";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { IChartApi } from "lightweight-charts";

export default function PairDetailPage() {
  const { setPageHeader } = usePageHeader();
  const params = useParams();
  const symbol = (params.symbol as string).toUpperCase();
  const [interval, setInterval] = useState("15m");

  useEffect(() => {
    setPageHeader(symbol, "Fiyat grafiği ve sinyal geçmişi");
    return () => setPageHeader("", "");
  }, [setPageHeader, symbol]);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const { data: candles, isLoading: loadingCandles } = useCandles(
    symbol,
    interval,
    300,
  );

  const { data: signals } = useSignals({ symbol, limit: 10 });

  const { data: sentiment } = useQuery({
    queryKey: ["sentiment", symbol],
    queryFn: async () => {
      const { data } = await api.get<SentimentData>(`/sentiment/${symbol}`);
      return data;
    },
  });

  useEffect(() => {
    if (!chartContainerRef.current || !candles?.length) return;

    let chart: IChartApi;

    const initChart = async () => {
      const { createChart, CandlestickSeries, HistogramSeries } =
        await import("lightweight-charts");

      if (chartRef.current) {
        chartRef.current.remove();
      }

      chart = createChart(chartContainerRef.current!, {
        layout: {
          background: { color: "transparent" },
          textColor: "#9ca3af",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.04)" },
          horzLines: { color: "rgba(255,255,255,0.04)" },
        },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
        timeScale: {
          borderColor: "rgba(255,255,255,0.1)",
          timeVisible: true,
        },
        width: chartContainerRef.current!.clientWidth,
        height: 400,
      });

      chartRef.current = chart;

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981",
        downColor: "#ef4444",
        borderUpColor: "#10b981",
        borderDownColor: "#ef4444",
        wickUpColor: "#10b981",
        wickDownColor: "#ef4444",
      });

      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });

      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const candleData = candles.map((c) => ({
        time: (new Date(c.open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
      }));

      const volumeData = candles.map((c) => ({
        time: (new Date(c.open_time).getTime() / 1000) as import("lightweight-charts").UTCTimestamp,
        value: Number(c.volume),
        color:
          Number(c.close) >= Number(c.open)
            ? "rgba(16,185,129,0.3)"
            : "rgba(239,68,68,0.3)",
      }));

      candleSeries.setData(candleData);
      volumeSeries.setData(volumeData);
      chart.timeScale().fitContent();
    };

    initChart();

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles]);

  return (
    <div className="space-y-4">
      {/* Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Fiyat Grafiği</CardTitle>
          <Tabs value={interval} onValueChange={setInterval}>
            <TabsList className="h-8">
              <TabsTrigger value="15m" className="text-xs px-3">
                15m
              </TabsTrigger>
              <TabsTrigger value="1h" className="text-xs px-3">
                1h
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          {loadingCandles ? (
            <Skeleton className="h-[400px]" />
          ) : (
            <div ref={chartContainerRef} />
          )}
        </CardContent>
      </Card>

      {/* Candle Stats */}
      {candles?.length ? (
        <div className="grid gap-4 sm:grid-cols-4">
          {(() => {
            const last = candles[candles.length - 1];
            return (
              <>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">Son Kapanış</p>
                    <p className="text-lg font-bold font-mono">
                      {formatPrice(last.close)}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">Yüksek</p>
                    <p className="text-lg font-bold font-mono text-emerald-500">
                      {formatPrice(last.high)}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">Düşük</p>
                    <p className="text-lg font-bold font-mono text-red-500">
                      {formatPrice(last.low)}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">Hacim</p>
                    <p className="text-lg font-bold font-mono">
                      {formatUSD(last.quote_volume)}
                    </p>
                  </CardContent>
                </Card>
              </>
            );
          })()}
        </div>
      ) : null}

      {/* Recent Signals */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Son Sinyaller</CardTitle>
        </CardHeader>
        <CardContent>
          {signals?.items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10 text-center">#</TableHead>
                  <TableHead className="hidden sm:table-cell">Tarih</TableHead>
                  <TableHead>Yön</TableHead>
                  <TableHead>Güven</TableHead>
                  <TableHead>Giriş</TableHead>
                  <TableHead>Durum</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.items.map((signal, index) => (
                  <TableRow key={signal.id}>
                    <TableCell className="text-center text-xs text-muted-foreground">
                      {index + 1}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-xs text-muted-foreground">
                      {formatDate(signal.created_at)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={signal.side} />
                    </TableCell>
                    <TableCell>
                      <ConfidenceBadge confidence={signal.confidence} />
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatPrice(signal.entry_price)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={signal.status} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Bu çift için sinyal yok
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
