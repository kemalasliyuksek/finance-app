"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface PageHeaderState {
  title: string;
  description: string;
}

interface PageHeaderContextType extends PageHeaderState {
  setPageHeader: (title: string, description?: string) => void;
}

const PageHeaderContext = createContext<PageHeaderContextType | null>(null);

export function PageHeaderProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PageHeaderState>({ title: "", description: "" });

  const setPageHeader = useCallback((title: string, description?: string) => {
    setState({ title, description: description ?? "" });
  }, []);

  return (
    <PageHeaderContext value={{ ...state, setPageHeader }}>
      {children}
    </PageHeaderContext>
  );
}

export function usePageHeader() {
  const ctx = useContext(PageHeaderContext);
  if (!ctx) throw new Error("usePageHeader must be used within PageHeaderProvider");
  return ctx;
}
