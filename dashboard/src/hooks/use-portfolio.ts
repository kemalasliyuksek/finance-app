import api from "@/lib/api-client";
import type { PortfolioSnapshot } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function usePortfolioCurrent() {
  return useQuery({
    queryKey: ["portfolio", "current"],
    queryFn: async () => {
      const { data } = await api.get<PortfolioSnapshot | null>(
        "/portfolio/current",
      );
      return data;
    },
    refetchInterval: 30000,
  });
}

export function usePortfolioHistory(range: string = "7d") {
  return useQuery({
    queryKey: ["portfolio", "history", range],
    queryFn: async () => {
      const { data } = await api.get<PortfolioSnapshot[]>(
        "/portfolio/history",
        { params: { range } },
      );
      return data;
    },
  });
}
