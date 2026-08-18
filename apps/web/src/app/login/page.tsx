"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";
import { b64ToBuf, bufferToB64 } from "@/lib/webauthn";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [need, setNeed] = useState<"login" | "totp" | "enroll">("login");
  const [code, setCode] = useState("");
  const [qr, setQr] = useState("");
  const [secret, setSecret] = useState("");
  const [recovery, setRecovery] = useState<string[]>([]);
  const [err, setErr] = useState("");

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const r = await api<{ need: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (r.need === "enroll_totp") {
        const en = await api<{ qr_png_base64: string; secret: string }>("/api/v1/auth/totp/enroll", { method: "POST" });
        setQr(en.qr_png_base64);
        setSecret(en.secret);
        setNeed("enroll");
      } else {
        setNeed("totp");
      }
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "login failed");
    }
  }

  async function loginPasskey() {
    setErr("");
    if (!email) {
      setErr("Enter your email first, then use a passkey.");
      return;
    }
    try {
      const opts = await api<{
        user_id: string;
        publicKey: {
          challenge: string;
          rpId?: string;
          timeout?: number;
          userVerification?: UserVerificationRequirement;
          allowCredentials?: { type: string; id: string }[];
        };
      }>(`/api/v1/auth/webauthn/login/options?email=${encodeURIComponent(email)}`);
      const pk = opts.publicKey;
      const cred = (await navigator.credentials.get({
        publicKey: {
          challenge: b64ToBuf(String(pk.challenge)),
          rpId: pk.rpId,
          timeout: pk.timeout,
          userVerification: pk.userVerification,
          allowCredentials: (pk.allowCredentials || []).map((c) => ({
            type: "public-key" as const,
            id: b64ToBuf(c.id),
          })),
        },
      })) as PublicKeyCredential | null;
      if (!cred) throw new Error("passkey cancelled");
      const ass = cred.response as AuthenticatorAssertionResponse;
      await api("/api/v1/auth/webauthn/login", {
        method: "POST",
        body: JSON.stringify({
          user_id: opts.user_id,
          id: cred.id,
          rawId: bufferToB64(cred.rawId),
          type: cred.type,
          response: {
            clientDataJSON: bufferToB64(ass.clientDataJSON),
            authenticatorData: bufferToB64(ass.authenticatorData),
            signature: bufferToB64(ass.signature),
            userHandle: ass.userHandle ? bufferToB64(ass.userHandle) : null,
          },
        }),
      });
      router.replace("/");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "passkey failed");
    }
  }

  async function submitTotp(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const path = need === "enroll" ? "/api/v1/auth/totp/confirm" : "/api/v1/auth/totp/verify";
      const r = await api<{ recovery_codes?: string[] }>(path, { method: "POST", body: JSON.stringify({ code }) });
      if (r.recovery_codes) {
        setRecovery(r.recovery_codes);
        return;
      }
      router.replace("/");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "totp failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">Private hub</p>
        <h1 className="display mt-2 text-4xl">HavenID</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">Your identity. Your screening number. Your rules.</p>

        {err ? <p className="mt-4 text-sm text-[var(--danger)]">{err}</p> : null}

        {recovery.length ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm">Save these recovery codes now. They will not be shown again.</p>
            <ul className="grid grid-cols-2 gap-2 font-mono text-sm">
              {recovery.map((c) => (
                <li key={c} className="rounded-md bg-[var(--bg-soft)] px-2 py-1">
                  {c}
                </li>
              ))}
            </ul>
            <Button onClick={() => router.replace("/")}>Continue to dashboard</Button>
          </div>
        ) : need === "login" ? (
          <form className="mt-6 space-y-4" onSubmit={submitLogin}>
            <Field label="Email">
              <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
            <Field label="Password">
              <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
            </Field>
            <Button type="submit" className="w-full">
              Continue
            </Button>
            <Button type="button" tone="soft" className="w-full" onClick={loginPasskey}>
              Use a passkey
            </Button>
            <a className="block text-center text-sm text-[var(--muted)] underline" href="/recover">
              Use a recovery code
            </a>
          </form>
        ) : (
          <form className="mt-6 space-y-4" onSubmit={submitTotp}>
            {need === "enroll" ? (
              <>
                <p className="text-sm text-[var(--muted)]">Scan this with your authenticator app, then enter a 6-digit code.</p>
                {qr ? <img src={`data:image/png;base64,${qr}`} alt="TOTP QR" className="mx-auto h-40 w-40 rounded-md bg-white p-2" /> : null}
                <p className="break-all font-mono text-xs text-[var(--muted)]">{secret}</p>
              </>
            ) : (
              <p className="text-sm text-[var(--muted)]">Enter the 6-digit code from your authenticator.</p>
            )}
            <Field label="Authentication code">
              <Input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} required />
            </Field>
            <Button type="submit" className="w-full">
              Verify
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
