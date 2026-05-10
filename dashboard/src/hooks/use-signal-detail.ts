"use client";

import api from "@/lib/api-client";
import type { SignalDetail } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useSignalDetail(signalId: string | null) {
  return useQuery({
    queryKey: ["signal-detail", signalId],
    queryFn: async () => {
      const { data } = await api.get<SignalDetail>(`/signals/${signalId}/detail`);
      return data;
    },
    enabled: !!signalId,
    refetchInterval: 10000,
  });
}
