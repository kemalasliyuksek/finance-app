import api from "@/lib/api-client";
import type { SandboxWalletResponse } from "@/types/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function useSandboxWallet() {
  return useQuery({
    queryKey: ["sandbox", "wallet"],
    queryFn: async () => {
      const { data } = await api.get<SandboxWalletResponse>("/sandbox/wallet");
      return data;
    },
    refetchInterval: 10000,
  });
}

export function useDeposit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ asset, amount }: { asset: string; amount: number }) => {
      const { data } = await api.post<SandboxWalletResponse>(
        "/sandbox/deposit",
        { asset, amount },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sandbox"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}

export function useResetSandbox() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/sandbox/reset");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
}
