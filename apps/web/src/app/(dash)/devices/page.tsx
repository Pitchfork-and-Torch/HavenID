"use client";

import { useEffect, useState } from "react";
import { Button, Input } from "@/components/ui";
import { api } from "@/lib/api";

type Device = { id: string; name: string; user_agent: string; last_ip: string; last_seen: string | null; revoked: boolean };

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});

  async function load() {
    const r = await api<{ devices: Device[] }>("/api/v1/devices");
    setDevices(r.devices);
    setNames(Object.fromEntries(r.devices.map((d) => [d.id, d.name])));
  }
  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="display text-3xl">Trusted devices</h1>
      <ul className="space-y-3">
        {devices.map((d) => (
          <li key={d.id} className="rounded-xl border border-[var(--line)] p-4">
            <div className="flex flex-wrap items-center gap-3">
              <Input value={names[d.id] || ""} onChange={(e) => setNames({ ...names, [d.id]: e.target.value })} />
              <Button
                tone="ghost"
                onClick={async () => {
                  await api(`/api/v1/devices/${d.id}`, { method: "PATCH", body: JSON.stringify({ name: names[d.id] }) });
                  await load();
                }}
              >
                Rename
              </Button>
              {!d.revoked ? (
                <Button
                  tone="danger"
                  onClick={async () => {
                    await api(`/api/v1/devices/${d.id}`, { method: "DELETE" });
                    await load();
                  }}
                >
                  Revoke
                </Button>
              ) : (
                <span className="text-sm text-[var(--muted)]">Revoked</span>
              )}
            </div>
            <p className="mt-2 text-xs text-[var(--muted)]">
              {d.last_ip} · {d.last_seen ? new Date(d.last_seen).toLocaleString() : ""} · {d.user_agent}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
