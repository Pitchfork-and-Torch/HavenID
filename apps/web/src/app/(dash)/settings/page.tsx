"use client";

import { useEffect, useState } from "react";
import { Button, Card, Field, Input } from "@/components/ui";
import { api, type Me } from "@/lib/api";

export default function SettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<Me>("/api/v1/me").then((m) => {
      setMe(m);
      setName(m.display_name);
      setPhone(m.phone_e164 || "");
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/me", { method: "PATCH", body: JSON.stringify({ display_name: name, phone_e164: phone }) });
    setMsg("Profile saved.");
  }

  async function theme(next: string) {
    await api("/api/v1/settings", { method: "PATCH", body: JSON.stringify({ theme: next }) });
    document.documentElement.dataset.theme = next === "light" ? "light" : "dark";
  }

  async function destroy() {
    await api("/api/v1/me", { method: "DELETE", body: JSON.stringify({ confirm }) });
    window.location.href = "/login";
  }

  if (!me) return <p>Loading...</p>;

  return (
    <div className="space-y-6">
      <h1 className="display text-3xl">Settings</h1>
      <Card>
        <form className="space-y-4" onSubmit={save}>
          <Field label="Display name">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Your real phone (optional)">
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <Button type="submit">Save</Button>
          {msg ? <span className="ml-3 text-sm text-[var(--ok)]">{msg}</span> : null}
        </form>
      </Card>
      <Card>
        <h2 className="display text-xl">Theme</h2>
        <div className="mt-3 flex gap-2">
          <Button tone="soft" onClick={() => theme("dark")}>
            Dark
          </Button>
          <Button tone="ghost" onClick={() => theme("light")}>
            Light
          </Button>
        </div>
      </Card>
      <Card>
        <h2 className="display text-xl">Export / delete</h2>
        <a className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-[var(--line)] px-3 text-sm" href="/api/v1/me/export">
          Download account export
        </a>
        <p className="mt-4 text-sm text-[var(--muted)]">Type your email to delete the account and all local data.</p>
        <div className="mt-2 flex gap-2">
          <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder={me.email} />
          <Button tone="danger" onClick={destroy}>
            Delete account
          </Button>
        </div>
      </Card>
    </div>
  );
}
