import api from "@/lib/api-client";
import type { PaginatedResponse, Signal } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function useSignals(params?: {
  status?: string;
  symbol?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}) {
  return useQuery({
    queryKey: ["signals", params],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Signal>>("/signals", {
        params,
      });
      return data;
    },
    refetchInterval: 60000, // Fallback — gerçek güncelleme WebSocket ile anlık gelir
  });
}

export function useApproveSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (signalId: string) => {
      const { data } = await api.post<Signal>(`/signals/${signalId}/approve`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useRejectSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (signalId: string) => {
      const { data } = await api.post<Signal>(`/signals/${signalId}/reject`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
