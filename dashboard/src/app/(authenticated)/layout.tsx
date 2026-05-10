"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { PageHeaderProvider } from "@/contexts/page-header-context";
import { SidebarProvider } from "@/contexts/sidebar-context";
import { useAuth } from "@/providers/auth-provider";
import { WebSocketProvider } from "@/providers/websocket-provider";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

const FORCE_CHANGE_PATH = "/change-password";

export default function AuthenticatedLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    // Zorunlu şifre değişikliği aktifken kullanıcı tüm sayfalardan
    // change-password'a yönlendirilir. Sonsuz döngüden kaçınmak için
    // o sayfanın kendisinde redirect tetiklenmez.
    if (mustChangePassword && pathname !== FORCE_CHANGE_PATH) {
      router.replace(FORCE_CHANGE_PATH);
    }
  }, [isAuthenticated, isLoading, mustChangePassword, pathname, router]);

  const onForceChangePath = pathname === FORCE_CHANGE_PATH;

  // Auth henüz hazır değilse veya redirect bekleniyorsa spinner göster.
  // Bu, eski sayfanın mount olup PageHeaderProvider olmadan
  // usePageHeader çağırmasını engeller.
  if (
    isLoading ||
    !isAuthenticated ||
    (mustChangePassword && !onForceChangePath)
  ) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // Zorunlu şifre değiştirme akışındayken sidebar/topbar/websocket'siz
  // sade bir layout göster — kullanıcı başka sayfaya geçişini engellemek için.
  if (mustChangePassword) {
    return (
      <main className="min-h-screen overflow-y-auto p-4 sm:p-6">
        {children}
      </main>
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
