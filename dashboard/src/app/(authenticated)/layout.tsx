"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { PageHeaderProvider } from "@/contexts/page-header-context";
import { SidebarProvider } from "@/contexts/sidebar-context";
import { useAuth } from "@/providers/auth-provider";
import { WebSocketProvider } from "@/providers/websocket-provider";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

export default function AuthenticatedLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <WebSocketProvider>
      <PageHeaderProvider>
        <SidebarProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col overflow-hidden">
              <Topbar />
              <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
            </div>
          </div>
        </SidebarProvider>
      </PageHeaderProvider>
    </WebSocketProvider>
  );
}
