"use client";

import api, { setAccessToken } from "@/lib/api-client";
import type { TokenResponse, UserInfo } from "@/types/api";
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
  mustChangePassword: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /** Şifre başarıyla değiştirildikten sonra flag'i düşür ve dashboard'a yönlendir. */
  clearMustChangePassword: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [username, setUsername] = useState<string | null>(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);
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
        return api.get<UserInfo>("/auth/me");
      })
      .then(({ data }) => {
        setUsername(data.username);
        setMustChangePassword(data.must_change_password);
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

      const forceChange = Boolean(data.must_change_password);
      setMustChangePassword(forceChange);

      if (forceChange) {
        router.push("/change-password");
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
    setMustChangePassword(false);
    router.push("/login");
  }, [router]);

  const clearMustChangePassword = useCallback(() => {
    setMustChangePassword(false);
    router.push("/dashboard");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        username,
        mustChangePassword,
        login,
        logout,
        clearMustChangePassword,
      }}
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
