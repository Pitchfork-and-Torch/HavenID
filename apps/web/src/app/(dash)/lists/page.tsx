"use client";

import { useEffect, useState } from "react";
import { Button, Card, Field, Input } from "@/components/ui";
import { api, type ListRow } from "@/lib/api";

export default function ListsPage() {
  const [items, setItems] = useState<ListRow[]>([]);
  const [pattern, setPattern] = useState("");
  const [kind, setKind] = useState("deny");
  const [match, setMatch] = useState("exact");

  async function load() {
    setItems((await api<{ items: ListRow[] }>("/api/v1/lists")).items);
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/lists", {
      method: "POST",
      body: JSON.stringify({ list_kind: kind, match_kind: match, pattern, note: "" }),
    });
    setPattern("");
    await load();
  }

  async function remove(id: string) {
    await api(`/api/v1/lists/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-3xl">Allow / deny</h1>
        <p className="text-sm text-[var(--muted)]">Exact numbers or prefixes such as +1800.</p>
      </div>
      <Card>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={add}>
          <Field label="List">
            <select className="min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="deny">Deny</option>
              <option value="allow">Allow</option>
            </select>
          </Field>
          <Field label="Match">
            <select className="min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3" value={match} onChange={(e) => setMatch(e.target.value)}>
              <option value="exact">Exact</option>
              <option value="prefix">Prefix</option>
            </select>
          </Field>
          <Field label="Pattern">
            <Input value={pattern} onChange={(e) => setPattern(e.target.value)} required />
          </Field>
          <div className="flex items-end">
            <Button type="submit">Add</Button>
          </div>
        </form>
      </Card>
      <ul className="divide-y divide-[var(--line)] rounded-xl border border-[var(--line)]">
        {items.map((row) => (
          <li key={row.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              <span className="mr-2 rounded-md bg-[var(--bg-soft)] px-2 py-0.5">{row.list_kind}</span>
              {row.pattern} ({row.match_kind})
            </span>
            <Button tone="ghost" onClick={() => remove(row.id)}>
              Remove
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
