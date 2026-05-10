"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ALL_CONFIG_FIELDS,
  ALL_CONFIG_KEYS,
} from "@/lib/config-fields";
import { cn } from "@/lib/utils";
import type { TradingConfig, TradingConfigUpdate } from "@/types/api";
import { ArrowRight, Download, Upload } from "lucide-react";
import { useRef, useState } from "react";

/** JSON dosyasında olabilecek her parametre için tek bir diff girdisi. */
type DiffKind = "change" | "same" | "invalid" | "unknown";

interface DiffEntry {
  key: string;
  kind: DiffKind;
  currentValue?: unknown;
  newValue?: unknown;
  reason?: string;
}

interface Props {
  config: TradingConfig;
  isPending: boolean;
  onApply: (updates: TradingConfigUpdate) => Promise<void>;
}

/** Config'i dışa/içe aktarmak için toolbar.
 *
 * - Dışa Aktar: 27 düzenlenebilir alanı JSON dosyası olarak indirir.
 * - İçe Aktar: dosya seçer, parse eder, diff önizlemesini dialog'da gösterir.
 *   Kullanıcı onaylarsa `onApply` mutation'ı tetiklenir.
 */
export function ConfigExportImport({ config, isPending, onApply }: Props) {
  const [diff, setDiff] = useState<DiffEntry[] | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    const exportable: Record<string, unknown> = {};
    for (const field of ALL_CONFIG_FIELDS) {
      const key = field.key as keyof TradingConfig;
      exportable[key as string] = config[key];
    }
    const json = JSON.stringify(exportable, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const date = new Date().toISOString().split("T")[0];
    a.download = `trading-config-${date}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleImportClick = () => {
    setImportError(null);
    fileRef.current?.click();
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // Aynı dosyayı tekrar seçebilmek için reset
    if (!file) return;

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setImportError("Geçersiz JSON: kök nesne (object) bekleniyor");
        return;
      }
      const computed = computeDiff(config, parsed as Record<string, unknown>);
      if (computed.length === 0) {
        setImportError("JSON içinde tanınan alan yok");
        return;
      }
      setDiff(computed);
    } catch (err) {
      setImportError(
        err instanceof Error ? `JSON parse hatası: ${err.message}` : "Dosya okunamadı",
      );
    }
  };

  const handleConfirm = async () => {
    if (!diff) return;
    const updates: TradingConfigUpdate = {};
    for (const entry of diff) {
      if (entry.kind === "change") {
        (updates as Record<string, unknown>)[entry.key] = entry.newValue;
      }
    }
    if (Object.keys(updates).length === 0) {
      setDiff(null);
      return;
    }
    setApplyError(null);
    try {
      await onApply(updates);
      setDiff(null);
    } catch (err: unknown) {
      setApplyError(extractErrorDetail(err));
    }
  };

  const handleCancel = () => {
    setDiff(null);
    setApplyError(null);
  };

  const changeCount = diff?.filter((d) => d.kind === "change").length ?? 0;
  const invalidCount = diff?.filter((d) => d.kind === "invalid").length ?? 0;
  const unknownCount = diff?.filter((d) => d.kind === "unknown").length ?? 0;

  return (
    <>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={isPending}
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          JSON Dışa Aktar
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleImportClick}
          disabled={isPending}
        >
          <Upload className="h-3.5 w-3.5 mr-1.5" />
          JSON İçe Aktar
        </Button>
        {importError && (
          <p className="text-xs text-destructive truncate" title={importError}>
            {importError}
          </p>
        )}
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={handleFileSelected}
        />
      </div>

      <Dialog open={diff !== null} onOpenChange={(open) => !open && handleCancel()}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>İçe Aktarma Önizlemesi</DialogTitle>
            <DialogDescription>
              {changeCount > 0
                ? `${changeCount} alan değişecek.`
                : "Değişiklik yok."}
              {invalidCount > 0 && ` ${invalidCount} geçersiz değer atlanacak.`}
              {unknownCount > 0 && ` ${unknownCount} bilinmeyen alan yoksayıldı.`}
            </DialogDescription>
          </DialogHeader>

          {diff && <DiffList entries={diff} />}

          {applyError && (
            <p className="text-xs text-destructive">{applyError}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isPending}
            >
              İptal
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleConfirm}
              disabled={isPending || changeCount === 0}
            >
              {isPending ? "Uygulanıyor..." : `${changeCount} Değişikliği Uygula`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// --- Diff görünümü ---

function DiffList({ entries }: { entries: DiffEntry[] }) {
  const changes = entries.filter((e) => e.kind === "change");
  const invalid = entries.filter((e) => e.kind === "invalid");
  const unknown = entries.filter((e) => e.kind === "unknown");

  return (
    <div className="max-h-[50vh] overflow-y-auto space-y-3 text-sm">
      {changes.length > 0 && (
        <Section label={`Değişecek (${changes.length})`} tone="change">
          {changes.map((e) => (
            <DiffRow key={e.key} entry={e} />
          ))}
        </Section>
      )}
      {invalid.length > 0 && (
        <Section label={`Geçersiz - atlanacak (${invalid.length})`} tone="invalid">
          {invalid.map((e) => (
            <DiffRow key={e.key} entry={e} />
          ))}
        </Section>
      )}
      {unknown.length > 0 && (
        <Section label={`Bilinmeyen - yoksayıldı (${unknown.length})`} tone="unknown">
          {unknown.map((e) => (
            <DiffRow key={e.key} entry={e} />
          ))}
        </Section>
      )}
      {changes.length === 0 && invalid.length === 0 && unknown.length === 0 && (
        <p className="text-muted-foreground text-xs">
          Tüm değerler mevcut ayarlarla aynı.
        </p>
      )}
    </div>
  );
}

function Section({
  label,
  tone,
  children,
}: {
  label: string;
  tone: "change" | "invalid" | "unknown";
  children: React.ReactNode;
}) {
  return (
    <div>
      <div
        className={cn(
          "text-[11px] font-medium uppercase tracking-wider mb-1.5",
          tone === "change" && "text-emerald-500",
          tone === "invalid" && "text-destructive",
          tone === "unknown" && "text-amber-500",
        )}
      >
        {label}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function DiffRow({ entry }: { entry: DiffEntry }) {
  if (entry.kind === "change") {
    return (
      <div className="flex items-center gap-2 text-xs font-mono tabular-nums border border-border rounded px-2 py-1.5">
        <span className="flex-1 text-muted-foreground truncate" title={entry.key}>
          {entry.key}
        </span>
        <span className="text-destructive/70 line-through">
          {formatValue(entry.currentValue)}
        </span>
        <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
        <span className="text-emerald-500 font-medium">
          {formatValue(entry.newValue)}
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2 text-xs font-mono tabular-nums text-muted-foreground border border-dashed border-border/50 rounded px-2 py-1">
      <span className="flex-1 truncate" title={entry.key}>
        {entry.key}
      </span>
      <span className="italic">{entry.reason ?? ""}</span>
    </div>
  );
}

// --- Diff hesaplama ---

function computeDiff(
  current: TradingConfig,
  incoming: Record<string, unknown>,
): DiffEntry[] {
  const entries: DiffEntry[] = [];

  // Önce incoming'deki bilinen alanlar
  for (const field of ALL_CONFIG_FIELDS) {
    const key = field.key as string;
    if (!(key in incoming)) continue;

    const raw = incoming[key];
    const parsed = parseIncomingValue(field.type, raw);

    if (parsed === undefined) {
      entries.push({
        key,
        kind: "invalid",
        newValue: raw,
        reason: `geçersiz ${field.type}`,
      });
      continue;
    }

    // Sayısal bound check (sadece sayısal tipler)
    if (typeof parsed === "number") {
      if (field.min !== undefined && parsed < field.min) {
        entries.push({
          key,
          kind: "invalid",
          newValue: parsed,
          reason: `< ${field.min}`,
        });
        continue;
      }
      if (field.max !== undefined && parsed > field.max) {
        entries.push({
          key,
          kind: "invalid",
          newValue: parsed,
          reason: `> ${field.max}`,
        });
        continue;
      }
    }

    const currentValue = current[key as keyof TradingConfig];
    if (valuesEqual(currentValue, parsed)) {
      entries.push({ key, kind: "same", currentValue, newValue: parsed });
    } else {
      entries.push({ key, kind: "change", currentValue, newValue: parsed });
    }
  }

  // Bilinmeyen alanlar
  for (const key of Object.keys(incoming)) {
    if (!ALL_CONFIG_KEYS.has(key)) {
      entries.push({
        key,
        kind: "unknown",
        newValue: incoming[key],
        reason: "bilinmeyen alan",
      });
    }
  }

  return entries;
}

function parseIncomingValue(
  type: "number" | "integer" | "percent" | "mode",
  raw: unknown,
): number | string | undefined {
  if (type === "mode") {
    if (raw === "semi_auto" || raw === "full_auto") return raw;
    return undefined;
  }
  if (typeof raw === "number" && Number.isFinite(raw)) {
    if (type === "integer" && !Number.isInteger(raw)) return undefined;
    return raw;
  }
  if (typeof raw === "string") {
    const n = Number(raw);
    if (!Number.isFinite(n)) return undefined;
    if (type === "integer" && !Number.isInteger(n)) return undefined;
    return n;
  }
  return undefined;
}

function valuesEqual(a: unknown, b: unknown): boolean {
  if (typeof a === "number" && typeof b === "number") {
    return Math.abs(a - b) < 1e-9;
  }
  return a === b;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toString();
  }
  return String(v);
}

function extractErrorDetail(err: unknown): string {
  if (typeof err === "object" && err !== null) {
    const e = err as {
      response?: { data?: { detail?: unknown } };
      message?: string;
    };
    const detail = e.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { msg?: string; loc?: unknown[] }) => {
          const path = Array.isArray(d.loc) ? d.loc.join(".") : "";
          return `${path}: ${d.msg}`;
        })
        .join("; ");
    }
    if (e.message) return e.message;
  }
  return "Uygulama başarısız";
}
