"use client";

import { useEffect, useState } from "react";
import { Button, Empty, Input } from "@/components/ui";
import { api, type CallRow } from "@/lib/api";

export default function CallsPage() {
  const [items, setItems] = useState<CallRow[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const r = await api<{ items: CallRow[] }>(`/api/v1/calls${q ? `?q=${encodeURIComponent(q)}` : ""}`);
    setItems(r.items);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function mark(id: string, kind: "spam" | "ok") {
    await api(`/api/v1/calls/${id}/mark-${kind}`, { method: "POST" });
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="display text-3xl">Calls</h1>
          <p className="text-sm text-[var(--muted)]">Filter, mark spam, feed the denylist.</p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            load().catch((er) => setErr(er.message));
          }}
        >
          <Input placeholder="Search number or reason" value={q} onChange={(e) => setQ(e.target.value)} />
          <Button type="submit">Filter</Button>
        </form>
      </div>
      {err ? <p className="text-[var(--danger)]">{err}</p> : null}
      {items.length === 0 ? (
        <Empty title="No calls" body="Inbound logs appear here after a real or simulated call." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--line)]">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-[var(--bg-soft)] text-[var(--muted)]">
              <tr>
                <th className="px-3 py-3">From</th>
                <th className="px-3 py-3">Decision</th>
                <th className="px-3 py-3">Score</th>
                <th className="px-3 py-3">When</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-t border-[var(--line)]">
                  <td className="px-3 py-3 font-medium">{c.from_e164 || "anonymous"}</td>
                  <td className="px-3 py-3">{c.decision}</td>
                  <td className="px-3 py-3 tabular-nums">{c.spam_score.toFixed(2)}</td>
                  <td className="px-3 py-3 text-[var(--muted)]">{c.started_at ? new Date(c.started_at).toLocaleString() : ""}</td>
                  <td className="px-3 py-3">
                    <div className="flex gap-2">
                      <Button tone="soft" onClick={() => mark(c.id, "spam")}>
                        Spam
                      </Button>
                      <Button tone="ghost" onClick={() => mark(c.id, "ok")}>
                        OK
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
