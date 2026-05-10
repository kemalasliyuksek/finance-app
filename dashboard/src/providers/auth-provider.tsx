"use client";

import api, { setAccessToken } from "@/lib/api-client";
import type { TokenResponse } from "@/types/api";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [username, setUsername] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      setIsLoading(false);
      return;
    }

    api
      .post<TokenResponse>("/auth/refresh", {
        refresh_token: refreshToken,
      })
      .then(({ data }) => {
        setAccessToken(data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        setIsAuthenticated(true);
        return api.get<{ username: string }>("/auth/me");
      })
      .then(({ data }) => {
        setUsername(data.username);
      })
      .catch(() => {
        localStorage.removeItem("refresh_token");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(
    async (user: string, password: string) => {
      const { data } = await api.post<TokenResponse>("/auth/login", {
        username: user,
        password,
      });
      setAccessToken(data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      setIsAuthenticated(true);
      setUsername(user);

      // Zorunlu şifre değişikliği kontrolü
      if (data.must_change_password) {
        router.push("/settings");
      } else {
        router.push("/dashboard");
      }
    },
    [router],
  );

  const logout = useCallback(() => {
    setAccessToken(null);
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    setUsername(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, username, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
