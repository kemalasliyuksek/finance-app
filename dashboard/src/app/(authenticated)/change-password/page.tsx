"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api-client";
import { useAuth } from "@/providers/auth-provider";
import { ShieldAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface ApiError {
  response?: { data?: { detail?: string | { msg?: string }[] } };
}

function extractError(err: unknown, fallback: string): string {
  const detail = (err as ApiError)?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

export default function ChangePasswordPage() {
  const { mustChangePassword, clearMustChangePassword, logout } = useAuth();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Yeni şifre ve doğrulama eşleşmiyor");
      return;
    }
    if (newPassword === currentPassword) {
      setError("Yeni şifre mevcut şifreyle aynı olamaz");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      // Flag düştü — context'i güncelle ve dashboard'a yönlendir
      clearMustChangePassword();
    } catch (err) {
      setError(extractError(err, "Şifre değiştirilemedi"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4 py-8">
      {mustChangePassword && (
        <Card className="border-amber-500/50 bg-amber-500/5">
          <CardContent className="flex gap-3 pt-6">
            <ShieldAlert className="h-5 w-5 shrink-0 text-amber-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Devam etmek için şifrenizi değiştirin
              </p>
              <p className="text-xs text-muted-foreground">
                Hesabınız varsayılan bir şifreyle oluşturuldu. Güvenliğiniz için
                lütfen yeni bir şifre belirleyin.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Şifre Değiştir</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current">Mevcut Şifre</Label>
              <Input
                id="current"
                type="password"
                autoComplete="current-password"
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
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
              <p className="text-xs text-muted-foreground">
                En az 8 karakter, 1 büyük harf, 1 küçük harf ve 1 rakam.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">Yeni Şifre (Tekrar)</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <Button type="submit" className="flex-1" disabled={submitting}>
                {submitting ? "Kaydediliyor..." : "Şifreyi Güncelle"}
              </Button>
              {!mustChangePassword && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push("/settings")}
                  disabled={submitting}
                >
                  İptal
                </Button>
              )}
              {mustChangePassword && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={logout}
                  disabled={submitting}
                >
                  Çıkış
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
