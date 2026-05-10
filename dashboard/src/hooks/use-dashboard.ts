import api from "@/lib/api-client";
import type { DashboardSummary } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async () => {
      const { data } = await api.get<DashboardSummary>("/dashboard/summary");
      return data;
    },
    refetchInterval: 30000,
  });
}
