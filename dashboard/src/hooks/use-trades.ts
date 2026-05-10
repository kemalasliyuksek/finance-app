import api from "@/lib/api-client";
import type { PaginatedResponse, Trade, TradeStats } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useTrades(params?: {
  status?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}) {
  return useQuery({
    queryKey: ["trades", params],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Trade>>("/trades", {
        params,
      });
      return data;
    },
    refetchInterval: 60000, // Fallback — gerçek güncelleme WebSocket ile anlık gelir
  });
}

export function useOpenTrades() {
  return useQuery({
    queryKey: ["trades", "open"],
    queryFn: async () => {
      const { data } = await api.get<Trade[]>("/trades/open");
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useTradeStats() {
  return useQuery({
    queryKey: ["trades", "stats"],
    queryFn: async () => {
      const { data } = await api.get<TradeStats>("/trades/stats");
      return data;
    },
  });
}
