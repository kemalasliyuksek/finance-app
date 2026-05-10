import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusColors: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-500 border-amber-500/20",
  approved: "bg-emerald-500/15 text-emerald-500 border-emerald-500/20",
  rejected: "bg-red-500/15 text-red-500 border-red-500/20",
  expired: "bg-orange-500/15 text-orange-500 border-orange-500/20",
  executed: "bg-blue-500/15 text-blue-500 border-blue-500/20",
  weak: "bg-zinc-500/15 text-zinc-500 border-zinc-500/20",
  open: "bg-emerald-500/15 text-emerald-500 border-emerald-500/20",
  closed: "bg-zinc-500/15 text-zinc-500 border-zinc-500/20",
  new: "bg-blue-500/15 text-blue-500 border-blue-500/20",
  submitted: "bg-amber-500/15 text-amber-500 border-amber-500/20",
  filled: "bg-emerald-500/15 text-emerald-500 border-emerald-500/20",
  cancelled: "bg-zinc-500/15 text-zinc-500 border-zinc-500/20",
  error: "bg-red-500/15 text-red-500 border-red-500/20",
  partially_filled: "bg-amber-500/15 text-amber-500 border-amber-500/20",
  BUY: "bg-emerald-500/15 text-emerald-500 border-emerald-500/20",
  SELL: "bg-red-500/15 text-red-500 border-red-500/20",
  sandbox: "bg-amber-500/15 text-amber-500 border-amber-500/20",
  live: "bg-emerald-500/15 text-emerald-500 border-emerald-500/20",
};

const statusLabels: Record<string, string> = {
  pending: "Bekliyor",
  approved: "Onaylandı",
  rejected: "Reddedildi",
  expired: "Süre Aşımı",
  executed: "Gerçekleşti",
  weak: "Zayıf",
  open: "Açık",
  closed: "Kapalı",
  new: "Yeni",
  submitted: "Gönderildi",
  filled: "Doldu",
  cancelled: "İptal",
  error: "Hata",
  partially_filled: "Kısmen Doldu",
  BUY: "AL",
  SELL: "SAT",
  sandbox: "Sandbox",
  live: "Canlı",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium",
        statusColors[status] ?? "bg-zinc-500/15 text-zinc-500",
      )}
    >
      {statusLabels[status] ?? status}
    </Badge>
  );
}
