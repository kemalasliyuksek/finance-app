import api from "@/lib/api-client";
import type { TradingConfig, TradingConfigUpdate } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const { data } = await api.get<TradingConfig>("/config");
      return data;
    },
  });
}

export function useUpdateConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (updates: TradingConfigUpdate) => {
      const { data } = await api.patch<TradingConfig>("/config", updates);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["config"], data);
      queryClient.invalidateQueries({ queryKey: ["config"] });
    },
  });
}
