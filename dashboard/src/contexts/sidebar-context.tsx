"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

interface SidebarContextType {
  isOpen: boolean;
  isCollapsed: boolean;
  toggle: () => void;
  close: () => void;
  toggleCollapse: () => void;
}

const SidebarContext = createContext<SidebarContextType | null>(null);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false); // mobil overlay
  const [isCollapsed, setIsCollapsed] = useState(false); // desktop collapse

  const toggle = useCallback(() => setIsOpen((v) => !v), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggleCollapse = useCallback(() => setIsCollapsed((v) => !v), []);

  // Ekran büyüdüğünde mobil overlay'i kapat
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const handler = () => { if (mq.matches) setIsOpen(false); };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return (
    <SidebarContext value={{ isOpen, isCollapsed, toggle, close, toggleCollapse }}>
      {children}
    </SidebarContext>
  );
}

export function useSidebar() {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar must be used within SidebarProvider");
  return ctx;
}
