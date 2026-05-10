"use client";

import { ConfigExportImport } from "@/components/settings/config-export-import";
import { EditableConfigSection } from "@/components/settings/editable-config-section";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePageHeader } from "@/contexts/page-header-context";
import { useConfig, useUpdateConfig } from "@/hooks/use-config";
import { useDeposit, useResetSandbox, useSandboxWallet } from "@/hooks/use-sandbox";
import api from "@/lib/api-client";
import {
  EXIT_FIELDS,
  MODE_FIELDS,
  RISK_FIELDS,
  SCREENER_FIELDS,
  SL_TP_FIELDS,
  STRATEGY_FIELDS,
} from "@/lib/config-fields";
import { formatAssetValue, formatUptime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BotStatus, TradingConfigUpdate } from "@/types/api";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Banknote,
  Bot,
  ChevronDown,
  Crosshair,
  KeyRound,
  RefreshCw,
  Shield,
  Sliders,
  Telescope,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";

export default function SettingsPage() {
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader("Ayarlar", "Bot yapılandırması ve hesap ayarları");
    return () => setPageHeader("", "");
  }, [setPageHeader]);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordError, setPasswordError] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [depositAmount, setDepositAmount] = useState("");
  const [depositMsg, setDepositMsg] = useState("");
  const [depositSuccess, setDepositSuccess] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);

  const { data: wallet } = useSandboxWallet();
  const deposit = useDeposit();
  const resetSandbox = useResetSandbox();
  const { data: config, isLoading: loadingConfig } = useConfig();
  const updateConfig = useUpdateConfig();

  const { data: status, isLoading: loadingStatus } = useQuery({
    queryKey: ["config", "status"],
    queryFn: async () => {
      const { data } = await api.get<BotStatus>("/config/status");
      return data;
    },
    refetchInterval: 10000,
  });

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordMsg("");
    setChangingPassword(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMsg("Şifre başarıyla değiştirildi");
      setPasswordError(false);
      setCurrentPassword("");
      setNewPassword("");
    } catch {
      setPasswordMsg("Mevcut şifre yanlış");
      setPasswordError(true);
    } finally {
      setChangingPassword(false);
    }
  }

  async function handleConfigSave(updates: TradingConfigUpdate) {
    await updateConfig.mutateAsync(updates);
  }

  if (loadingConfig || loadingStatus || !config) {
    return (
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-48" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Bot Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Bot Durumu
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Mod</p>
              <p
                className={cn(
                  "text-sm font-medium",
                  status?.app_mode === "live"
                    ? "text-emerald-500"
                    : status?.app_mode === "sandbox"
                      ? "text-amber-500"
                      : "text-zinc-500",
                )}
              >
                {status?.app_mode?.toUpperCase()}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Trading Modu</p>
              <p className="text-sm font-medium">
                {status?.trading_mode === "semi_auto"
                  ? "Yarı Otomatik"
                  : "Tam Otomatik"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Uptime</p>
              <p className="text-sm font-medium font-mono">
                {formatUptime(status?.uptime_seconds ?? 0)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Aktif Çiftler</p>
              <p className="text-sm font-medium">
                {status?.active_pairs?.length ?? 0}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sandbox Cüzdan */}
      {status?.is_sandbox && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Banknote className="h-4 w-4" />
              Sandbox Cüzdan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {wallet?.balances && wallet.balances.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Varlık</TableHead>
                    <TableHead>Serbest</TableHead>
                    <TableHead>Kilitli</TableHead>
                    <TableHead>Toplam</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {wallet.balances.map((b) => (
                    <TableRow key={b.asset}>
                      <TableCell className="font-mono font-medium">{b.asset}</TableCell>
                      <TableCell className="font-mono text-xs">{formatAssetValue(b.asset, b.free)}</TableCell>
                      <TableCell className="font-mono text-xs">{formatAssetValue(b.asset, b.locked)}</TableCell>
                      <TableCell className="font-mono text-xs font-medium">{formatAssetValue(b.asset, b.total)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">
                Henüz bakiye yüklenmedi. Aşağıdan USDT yükleyin.
              </p>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                const amount = parseFloat(depositAmount);
                if (amount > 0) {
                  setDepositMsg("");
                  deposit.mutate(
                    { asset: "USDT", amount },
                    {
                      onSuccess: () => {
                        setDepositAmount("");
                        setDepositMsg(`${amount} USDT yüklendi`);
                        setDepositSuccess(true);
                      },
                      onError: (err: unknown) => {
                        const detail =
                          (err as { response?: { data?: { detail?: string } } })
                            ?.response?.data?.detail || "Yükleme başarısız";
                        setDepositMsg(detail);
                        setDepositSuccess(false);
                      },
                    },
                  );
                }
              }}
              className="flex items-end gap-2 max-w-sm"
            >
              <div className="flex-1 space-y-2">
                <Label htmlFor="deposit">USDT Yükle</Label>
                <Input
                  id="deposit"
                  type="number"
                  placeholder="10000"
                  min="1"
                  step="any"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" disabled={deposit.isPending}>
                {deposit.isPending ? "Yükleniyor..." : "Yükle"}
              </Button>
            </form>
            {depositMsg && (
              <p className={cn("text-sm", depositSuccess ? "text-emerald-500" : "text-destructive")}>
                {depositMsg}
              </p>
            )}

            <div className="pt-2 border-t border-border">
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  if (
                    confirm(
                      "Tüm sandbox verisi silinecek (cüzdan, trade'ler, emirler, sinyaller). Emin misiniz?",
                    )
                  ) {
                    resetSandbox.mutate();
                  }
                }}
                disabled={resetSandbox.isPending}
              >
                <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                {resetSandbox.isPending ? "Sıfırlanıyor..." : "Sandbox Sıfırla"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Change Password */}
      <Card>
        <button
          type="button"
          onClick={() => setPasswordOpen(!passwordOpen)}
          className="flex w-full items-center justify-between px-6 py-4"
        >
          <div className="flex items-center gap-2 text-base font-semibold">
            <KeyRound className="h-4 w-4" />
            Şifre Değiştir
          </div>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              passwordOpen && "rotate-180",
            )}
          />
        </button>
        {passwordOpen && (
          <CardContent className="pt-0">
            <form onSubmit={handleChangePassword}>
              <div className="grid grid-cols-3 gap-4 items-end">
                <div className="space-y-2">
                  <Label htmlFor="current">Mevcut Şifre</Label>
                  <Input
                    id="current"
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new">Yeni Şifre</Label>
                  <Input
                    id="new"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                </div>
                <Button type="submit" disabled={changingPassword}>
                  {changingPassword ? "Değiştiriliyor..." : "Şifreyi Değiştir"}
                </Button>
              </div>
              {passwordMsg && (
                <p
                  className={cn(
                    "text-sm mt-3",
                    passwordError ? "text-destructive" : "text-emerald-500",
                  )}
                >
                  {passwordMsg}
                </p>
              )}
            </form>
          </CardContent>
        )}
      </Card>

      {/* Config düzenleme başlığı + Export/Import */}
      <div className="flex items-center justify-between gap-2 pt-2">
        <div>
          <h3 className="text-sm font-semibold">Trading Parametreleri</h3>
          <p className="text-xs text-muted-foreground">
            Değişiklikler anında uygulanır (hot reload) ve DB'de kalıcıdır.
          </p>
        </div>
        <ConfigExportImport
          config={config}
          isPending={updateConfig.isPending}
          onApply={handleConfigSave}
        />
      </div>

      {/* Düzenlenebilir config kartları — 3 kolon grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <EditableConfigSection
          title="Trading Modu"
          icon={Bot}
          fields={MODE_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
        <EditableConfigSection
          title="Risk Parametreleri"
          icon={Shield}
          fields={RISK_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
        <EditableConfigSection
          title="Strateji Parametreleri"
          icon={TrendingUp}
          fields={STRATEGY_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
        <EditableConfigSection
          title="Stop-Loss / Take-Profit"
          icon={Crosshair}
          fields={SL_TP_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
        <EditableConfigSection
          title="Çıkış Stratejisi"
          icon={Sliders}
          fields={EXIT_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
        <EditableConfigSection
          title="Screener Parametreleri"
          icon={Telescope}
          fields={SCREENER_FIELDS}
          values={config}
          isPending={updateConfig.isPending}
          onSave={handleConfigSave}
        />
      </div>
    </div>
  );
}
