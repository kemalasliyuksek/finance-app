import api from "@/lib/api-client";
import type { ScreenerResultsResponse, ScreenerStatus } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useScreenerResults() {
  return useQuery({
    queryKey: ["screener", "results"],
    queryFn: async () => {
      const { data } = await api.get<ScreenerResultsResponse>(
        "/screener/results",
      );
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useScreenerStatus() {
  return useQuery({
    queryKey: ["screener", "status"],
    queryFn: async () => {
      const { data } = await api.get<ScreenerStatus>("/screener/status");
      return data;
    },
    refetchInterval: 30000,
  });
}
