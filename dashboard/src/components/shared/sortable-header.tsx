"use client";

import { TableHead } from "@/components/ui/table";
import type { SortConfig } from "@/hooks/use-table-sort";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronUp, ChevronsUpDown } from "lucide-react";

interface SortableHeaderProps {
  label: string;
  sortKey: string;
  currentSort: SortConfig;
  onSort: (key: string) => void;
  className?: string;
}

export function SortableHeader({ label, sortKey, currentSort, onSort, className }: SortableHeaderProps) {
  const isActive = currentSort.key === sortKey;

  return (
    <TableHead
      className={cn("cursor-pointer select-none hover:text-foreground transition-colors", className)}
      onClick={() => onSort(sortKey)}
    >
      <div className="flex items-center gap-1">
        {label}
        {isActive ? (
          currentSort.direction === "asc" ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )
        ) : (
          <ChevronsUpDown className="h-3 w-3 opacity-30" />
        )}
      </div>
    </TableHead>
  );
}
