"use client";

import { useState } from "react";
import { Button, Card, Field, Input } from "@/components/ui";
import { api } from "@/lib/api";

export default function RecoverPage() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api("/api/v1/auth/recover", {
        method: "POST",
        body: JSON.stringify({ email, code, new_password: password }),
      });
      setMsg("Password reset. Sign in and enroll a new authenticator.");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "recovery failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <h1 className="display text-3xl">Recover access</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">Use an unused recovery code. TOTP will be reset.</p>
        {err ? <p className="mt-3 text-sm text-[var(--danger)]">{err}</p> : null}
        {msg ? <p className="mt-3 text-sm text-[var(--ok)]">{msg}</p> : null}
        <form className="mt-6 space-y-4" onSubmit={submit}>
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Recovery code">
            <Input value={code} onChange={(e) => setCode(e.target.value)} required />
          </Field>
          <Field label="New password" hint="At least 12 characters">
            <Input type="password" minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <Button type="submit" className="w-full">
            Reset
          </Button>
          <a className="block text-center text-sm underline" href="/login">
            Back to sign in
          </a>
        </form>
      </Card>
    </div>
  );
}
