"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import api from "@/lib/api-client";
import type { BotStatus } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePageHeader } from "@/contexts/page-header-context";
import { CandlestickChart, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function PairsPage() {
  const queryClient = useQueryClient();
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("Takip Edilenler", "Aktif trading çiftleri yönetimi");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [newPair, setNewPair] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: status, isLoading } = useQuery({
    queryKey: ["config", "status"],
    queryFn: async () => {
      const { data } = await api.get<BotStatus>("/config/status");
      return data;
    },
  });

  const addPair = useMutation({
    mutationFn: async (symbol: string) => {
      await api.post("/config/pairs", { symbol });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config"] });
      setNewPair("");
      setDialogOpen(false);
    },
  });

  const removePair = useMutation({
    mutationFn: async (symbol: string) => {
      await api.delete(`/config/pairs/${symbol}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });

  const pairs = status?.active_pairs ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-1 h-4 w-4" />
          Çift Ekle
        </Button>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Trading Çifti Ekle</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Sembol</Label>
                <Input
                  placeholder="ör. LINKUSDT"
                  value={newPair}
                  onChange={(e) => setNewPair(e.target.value.toUpperCase())}
                />
              </div>
              <Button
                className="w-full"
                onClick={() => addPair.mutate(newPair)}
                disabled={!newPair || addPair.isPending}
              >
                {addPair.isPending ? "Ekleniyor..." : "Ekle"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {pairs.map((symbol) => (
            <Card key={symbol} className="group relative">
              <Link href={`/pairs/${symbol}`}>
                <CardContent className="flex items-center gap-3 pt-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <CandlestickChart className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-mono text-sm font-bold">{symbol}</p>
                    <p className="text-xs text-muted-foreground">
                      {symbol.replace("USDT", "")} / USDT
                    </p>
                  </div>
                </CardContent>
              </Link>
              <Button
                size="icon"
                variant="ghost"
                className="absolute right-2 top-2 h-7 w-7 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-500"
                onClick={() => removePair.mutate(symbol)}
                disabled={removePair.isPending}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
