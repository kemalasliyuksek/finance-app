import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number;
  threshold?: number;
}

export function ConfidenceBadge({
  confidence,
  threshold = 0.6,
}: ConfidenceBadgeProps) {
  const pct = Number(confidence) * 100;
  const midThreshold = threshold - 0.1; // 0.5

  let colorClass: string;
  let bgClass: string;

  if (confidence >= threshold) {
    colorClass = "text-emerald-500";
    bgClass = "bg-emerald-500/15 border-emerald-500/20";
  } else if (confidence >= midThreshold) {
    colorClass = "text-amber-500";
    bgClass = "bg-amber-500/15 border-amber-500/20";
  } else {
    colorClass = "text-red-500";
    bgClass = "bg-red-500/15 border-red-500/20";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-mono font-medium",
        bgClass,
        colorClass,
      )}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", {
          "bg-emerald-500": confidence >= threshold,
          "bg-amber-500": confidence >= midThreshold && confidence < threshold,
          "bg-red-500": confidence < midThreshold,
        })}
      />
      {pct.toFixed(0)}%
    </span>
  );
}
