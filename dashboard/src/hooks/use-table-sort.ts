"use client";

import { useMemo, useState } from "react";

export interface SortConfig {
  key: string;
  direction: "asc" | "desc";
}

export function useTableSort<T>(
  data: T[],
  defaultKey: string,
  defaultDirection: "asc" | "desc" = "desc",
) {
  const [sort, setSort] = useState<SortConfig>({ key: defaultKey, direction: defaultDirection });

  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sort.key];
      const bVal = (b as Record<string, unknown>)[sort.key];

      // null/undefined sona
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === "number" && typeof bVal === "number") {
        cmp = aVal - bVal;
      } else if (typeof aVal === "string" && typeof bVal === "string") {
        // Tarih string kontrolü (ISO format)
        if (aVal.match(/^\d{4}-\d{2}-\d{2}/) && bVal.match(/^\d{4}-\d{2}-\d{2}/)) {
          cmp = new Date(aVal).getTime() - new Date(bVal).getTime();
        } else {
          cmp = aVal.localeCompare(bVal, "tr");
        }
      } else {
        cmp = String(aVal).localeCompare(String(bVal), "tr");
      }

      return sort.direction === "asc" ? cmp : -cmp;
    });
  }, [data, sort]);

  const toggleSort = (key: string) => {
    setSort((prev) => ({
      key,
      direction: prev.key === key && prev.direction === "desc" ? "asc" : "desc",
    }));
  };

  return { sortedData, sort, toggleSort };
}
