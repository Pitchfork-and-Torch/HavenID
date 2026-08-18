"use client";

import { useEffect, useState } from "react";
import { Button, Card, Empty, Field, Input } from "@/components/ui";
import { api, type Contact } from "@/lib/api";

export default function ContactsPage() {
  const [items, setItems] = useState<Contact[]>([]);
  const [q, setQ] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vcard, setVcard] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const r = await api<{ items: Contact[] }>(`/api/v1/contacts${q ? `?q=${encodeURIComponent(q)}` : ""}`);
    setItems(r.items);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/contacts", {
      method: "POST",
      body: JSON.stringify({ display_name: name, phones: phone ? [{ e164: phone }] : [] }),
    });
    setName("");
    setPhone("");
    await load();
  }

  async function remove(id: string) {
    await api(`/api/v1/contacts/${id}`, { method: "DELETE" });
    await load();
  }

  async function importVcard(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/contacts/import", { method: "POST", body: JSON.stringify({ vcard }) });
    setVcard("");
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-3xl">Contacts</h1>
        <p className="text-sm text-[var(--muted)]">Known numbers skip the challenge in balanced mode.</p>
      </div>
      {err ? <p className="text-[var(--danger)]">{err}</p> : null}
      <Card>
        <form className="grid gap-3 md:grid-cols-3" onSubmit={create}>
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Phone">
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1..." />
          </Field>
          <div className="flex items-end">
            <Button type="submit">Add contact</Button>
          </div>
        </form>
      </Card>
      <div className="flex gap-2">
        <Input placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button
          tone="ghost"
          onClick={() =>
            load().catch((e) => setErr(e.message))
          }
        >
          Search
        </Button>
        <a className="inline-flex min-h-11 items-center rounded-lg border border-[var(--line)] px-3 text-sm" href="/api/v1/contacts/export">
          Export vCard
        </a>
      </div>
      {items.length === 0 ? (
        <Empty title="No contacts" body="Add one above or import a vCard." />
      ) : (
        <ul className="divide-y divide-[var(--line)] rounded-xl border border-[var(--line)]">
          {items.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-medium">{c.display_name}</p>
                <p className="text-sm text-[var(--muted)]">{c.phones.map((p) => p.e164).join(" ") || "no number"}</p>
              </div>
              <Button tone="ghost" onClick={() => remove(c.id)}>
                Delete
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Card>
        <h2 className="display text-xl">Import vCard</h2>
        <form className="mt-3 space-y-3" onSubmit={importVcard}>
          <textarea
            className="min-h-32 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] p-3 text-sm"
            value={vcard}
            onChange={(e) => setVcard(e.target.value)}
            placeholder="BEGIN:VCARD..."
          />
          <Button type="submit">Import</Button>
        </form>
      </Card>
    </div>
  );
}
