import api from "@/lib/api-client";
import type { BinanceAccountResponse } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useBinanceAccount() {
  return useQuery({
    queryKey: ["binance", "account"],
    queryFn: async () => {
      const { data } = await api.get<BinanceAccountResponse>(
        "/binance/account",
      );
      return data;
    },
    retry: false,
    refetchInterval: 60000,
  });
}
