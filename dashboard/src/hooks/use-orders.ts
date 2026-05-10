import api from "@/lib/api-client";
import type { Order, PaginatedResponse } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useOrders(params?: {
  status?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Order>>("/orders", {
        params,
      });
      return data;
    },
    refetchInterval: 60000, // Fallback — gerçek güncelleme WebSocket ile anlık gelir
  });
}
