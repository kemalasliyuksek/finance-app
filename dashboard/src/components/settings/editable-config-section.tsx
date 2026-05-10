"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { TradingConfig, TradingConfigUpdate } from "@/types/api";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

/** Editable config alanının UI tanımı. */
export interface FieldDef {
  key: keyof TradingConfigUpdate;
  label: string;
  hint?: string;
  /** "number" = ondalıklı, "integer" = tamsayı,
   *  "percent" = 0-1 arası (görüntü ayarları), "mode" = trading_mode toggle. */
  type: "number" | "integer" | "percent" | "mode";
  min?: number;
  max?: number;
  step?: number;
}

interface Props {
  title: string;
  icon: LucideIcon;
  fields: FieldDef[];
  values: TradingConfig;
  isPending: boolean;
  onSave: (updates: TradingConfigUpdate) => Promise<void> | void;
}

/** Bir konfigürasyon grubunu compact düzenlenebilir form olarak render eder.
 *
 * Tek kolon stacked layout — kartın kendisi dışarıdaki grid içinde yerleşir.
 * Sadece değişen alanlar PATCH'e gönderilir. WebSocket reload ile draft
 * otomatik senkron tutulur.
 */
export function EditableConfigSection({
  title,
  icon: Icon,
  fields,
  values,
  isPending,
  onSave,
}: Props) {
  const initial = useMemo(() => toDraft(fields, values), [fields, values]);
  const [draft, setDraft] = useState<Record<string, string>>(initial);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    setDraft(toDraft(fields, values));
  }, [fields, values]);

  const dirty = useMemo(() => {
    for (const f of fields) {
      if (draft[f.key] !== initial[f.key]) return true;
    }
    return false;
  }, [draft, initial, fields]);

  const handleChange = (key: string, value: string) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setMessage(null);
  };

  const handleReset = () => {
    setDraft(initial);
    setMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    const updates: TradingConfigUpdate = {};
    for (const f of fields) {
      if (draft[f.key] === initial[f.key]) continue;
      const parsed = parseDraftValue(f, draft[f.key]);
      if (parsed === undefined) {
        setMessage({ text: `${f.label}: geçersiz değer`, ok: false });
        return;
      }
      (updates as Record<string, unknown>)[f.key] = parsed;
    }

    if (Object.keys(updates).length === 0) return;

    try {
      await onSave(updates);
      setMessage({ text: "Kaydedildi", ok: true });
    } catch (err: unknown) {
      setMessage({ text: extractErrorDetail(err), ok: false });
    }
  };

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        <form onSubmit={handleSubmit} className="flex flex-col flex-1">
          <div className="space-y-3 flex-1">
            {fields.map((f) => (
              <FieldInput
                key={f.key as string}
                field={f}
                value={draft[f.key] ?? ""}
                onChange={(v) => handleChange(f.key as string, v)}
                disabled={isPending}
              />
            ))}
          </div>

          <div className="flex items-center gap-2 pt-3 mt-3 border-t border-border">
            <Button type="submit" size="sm" disabled={!dirty || isPending}>
              {isPending ? "Kaydediliyor..." : "Kaydet"}
            </Button>
            {dirty && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleReset}
                disabled={isPending}
              >
                İptal
              </Button>
            )}
            {message && (
              <p
                className={cn(
                  "text-xs ml-auto truncate",
                  message.ok ? "text-emerald-500" : "text-destructive",
                )}
                title={message.text}
              >
                {message.text}
              </p>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function FieldInput({
  field,
  value,
  onChange,
  disabled,
}: {
  field: FieldDef;
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  if (field.type === "mode") {
    return (
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">{field.label}</Label>
        <div className="flex gap-1.5">
          <Button
            type="button"
            variant={value === "semi_auto" ? "default" : "outline"}
            size="sm"
            className="flex-1"
            onClick={() => onChange("semi_auto")}
            disabled={disabled}
          >
            Yarı Otomatik
          </Button>
          <Button
            type="button"
            variant={value === "full_auto" ? "default" : "outline"}
            size="sm"
            className="flex-1"
            onClick={() => onChange("full_auto")}
            disabled={disabled}
          >
            Tam Otomatik
          </Button>
        </div>
        {field.hint && (
          <p className="text-[11px] text-muted-foreground leading-snug">
            {field.hint}
          </p>
        )}
      </div>
    );
  }

  // Spin butonları gizli olduğundan step sadece form validation'ı
  // etkileyecektir. "any" kullanarak, tip ve min/max kontrolü dışında
  // kullanıcı istediği değeri yazabilir (ör. 0.02 gibi step'e tam
  // oturmayan değerler reddedilmez).
  const htmlStep = field.type === "integer" ? 1 : "any";

  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-2">
      <Label
        htmlFor={field.key as string}
        className="text-xs text-muted-foreground leading-tight"
      >
        {field.label}
        {field.hint && (
          <span
            className="text-[10px] text-muted-foreground/70 block mt-0.5"
            title={field.hint}
          >
            {field.hint}
          </span>
        )}
      </Label>
      <Input
        id={field.key as string}
        type="number"
        min={field.min}
        max={field.max}
        step={htmlStep}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onWheel={(e) => e.currentTarget.blur()}
        disabled={disabled}
        className="h-8 w-28 text-sm font-mono tabular-nums text-right [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:m-0 [&::-webkit-outer-spin-button]:appearance-none"
      />
    </div>
  );
}

// --- Yardımcılar ---

function toDraft(
  fields: FieldDef[],
  values: TradingConfig,
): Record<string, string> {
  const draft: Record<string, string> = {};
  for (const f of fields) {
    const raw = values[f.key as keyof TradingConfig];
    if (f.type === "mode") {
      draft[f.key as string] = String(raw ?? "semi_auto");
    } else {
      draft[f.key as string] = String(raw ?? "");
    }
  }
  return draft;
}

function parseDraftValue(
  field: FieldDef,
  raw: string,
): number | string | undefined {
  if (field.type === "mode") {
    if (raw === "semi_auto" || raw === "full_auto") return raw;
    return undefined;
  }
  if (raw === "" || raw === undefined) return undefined;
  const n = Number(raw);
  if (!Number.isFinite(n)) return undefined;
  if (field.type === "integer" && !Number.isInteger(n)) return undefined;
  if (field.min !== undefined && n < field.min) return undefined;
  if (field.max !== undefined && n > field.max) return undefined;
  return n;
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
  return "Kaydetme başarısız";
}
