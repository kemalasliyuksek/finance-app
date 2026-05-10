import { format, formatDistanceToNow } from "date-fns";
import { tr } from "date-fns/locale";

export function formatUSD(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatPrice(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  if (num >= 1000) return formatUSD(num);
  if (num >= 1) return `$${num.toFixed(4)}`;
  return `$${num.toFixed(6)}`;
}

export function formatPercent(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  const sign = num > 0 ? "+" : "";
  return `${sign}${(num * 100).toFixed(2)}%`;
}

export function formatQuantity(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  if (num >= 1) return num.toFixed(4);
  return num.toFixed(8);
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "-";
  return format(new Date(date), "dd.MM.yyyy HH:mm", { locale: tr });
}

export function formatTimeAgo(date: string | null | undefined): string {
  if (!date) return "-";
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: tr });
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}sa ${m}dk`;
  return `${m}dk`;
}

export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}g ${h}sa`;
  if (h > 0) return `${h}sa ${m}dk`;
  return `${m}dk`;
}

export function formatVolume(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  if (num >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(1)}B`;
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `$${(num / 1_000).toFixed(1)}K`;
  return `$${num.toFixed(0)}`;
}

export function formatChangePercent(value: number | string | null | undefined): string {
  const num = Number(value ?? 0);
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

const FIAT_SYMBOLS: Record<string, string> = { TRY: "₺", EUR: "€", GBP: "£" };
const STABLECOINS = new Set(["USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI"]);

export function formatAssetValue(asset: string, value: number): string {
  if (value === 0) return "0";
  if (FIAT_SYMBOLS[asset]) return `${FIAT_SYMBOLS[asset]}${value.toFixed(2)}`;
  if (STABLECOINS.has(asset)) return `$${value.toFixed(2)}`;
  if (value >= 1) return value.toFixed(4);
  if (value >= 0.0001) return value.toFixed(6);
  return value.toFixed(8);
}
