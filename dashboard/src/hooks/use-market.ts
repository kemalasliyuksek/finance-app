import api from "@/lib/api-client";
import type { FavoritesResponse, MarketCoinsResponse } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function useMarketCoins(window: "1h" | "4h" | "1d" = "1d") {
  return useQuery({
    queryKey: ["market", "coins", window],
    queryFn: async () => {
      const { data } = await api.get<MarketCoinsResponse>("/market/coins", {
        params: { window },
      });
      return data;
    },
    refetchInterval: 60000,
  });
}

export function useFavorites() {
  return useQuery({
    queryKey: ["market", "favorites"],
    queryFn: async () => {
      const { data } = await api.get<FavoritesResponse>("/market/favorites");
      return data;
    },
  });
}

export function useAddFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (symbol: string) => {
      await api.post("/market/favorites", { symbol });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market", "favorites"] });
    },
  });
}

export function useRemoveFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (symbol: string) => {
      await api.delete(`/market/favorites/${symbol}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["market", "favorites"] });
    },
  });
}
