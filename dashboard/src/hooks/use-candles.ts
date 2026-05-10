import api from "@/lib/api-client";
import type { Candle } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

export function useCandles(
  symbol: string,
  interval: string,
  limit: number = 200,
) {
  return useQuery({
    queryKey: ["candles", symbol, interval, limit],
    queryFn: async () => {
      const { data } = await api.get<Candle[]>(
        `/candles/${symbol}/${interval}`,
        { params: { limit } },
      );
      return data;
    },
    enabled: !!symbol && !!interval,
  });
}
