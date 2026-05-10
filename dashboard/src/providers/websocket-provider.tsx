"use client";

import { getAccessToken } from "@/lib/api-client";
import { TradingWebSocket, type WebSocketMessage } from "@/lib/websocket";
import { useAuth } from "@/providers/auth-provider";
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface WSContextType {
  isConnected: boolean;
  subscribe: (handler: (msg: WebSocketMessage) => void) => () => void;
}

const WSContext = createContext<WSContextType>({
  isConnected: false,
  subscribe: () => () => {},
});

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const wsRef = useRef<TradingWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;

    const token = getAccessToken();
    if (!token) return;

    const ws = new TradingWebSocket(WS_URL, token);
    wsRef.current = ws;

    const unsub = ws.subscribe((msg) => {
      switch (msg.type) {
        case "signal":
          queryClient.invalidateQueries({ queryKey: ["signals"] });
          queryClient.invalidateQueries({ queryKey: ["dashboard"] });
          break;
        case "order":
          queryClient.invalidateQueries({ queryKey: ["orders"] });
          queryClient.invalidateQueries({ queryKey: ["trades"] });
          queryClient.invalidateQueries({ queryKey: ["dashboard"] });
          queryClient.invalidateQueries({ queryKey: ["sandbox"] });
          break;
        case "candle":
          queryClient.invalidateQueries({ queryKey: ["candles"] });
          break;
        case "sentiment":
          queryClient.invalidateQueries({ queryKey: ["sentiment"] });
          break;
        case "config":
          queryClient.invalidateQueries({ queryKey: ["config"] });
          queryClient.invalidateQueries({ queryKey: ["screener"] });
          break;
        case "screener":
          queryClient.invalidateQueries({ queryKey: ["screener"] });
          break;
      }
    });

    ws.connect();

    const checkConnection = setInterval(() => {
      setIsConnected(ws.isConnected);
    }, 2000);

    return () => {
      unsub();
      clearInterval(checkConnection);
      ws.disconnect();
      wsRef.current = null;
    };
  }, [isAuthenticated, queryClient]);

  const subscribe = (handler: (msg: WebSocketMessage) => void) => {
    return wsRef.current?.subscribe(handler) ?? (() => {});
  };

  return (
    <WSContext.Provider value={{ isConnected, subscribe }}>
      {children}
    </WSContext.Provider>
  );
}

export function useWebSocket() {
  return useContext(WSContext);
}
