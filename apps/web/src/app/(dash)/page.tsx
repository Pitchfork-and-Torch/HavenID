"use client";

import { useEffect, useState } from "react";
import { Card, StatusDot } from "@/components/ui";
import { api, type CallRow } from "@/lib/api";

type Overview = {
  calls_total: number;
  calls_blocked: number;
  contacts: number;
  devices: number;
  policy_mode: string;
  twilio_ok: boolean;
  twilio_phone: string;
  twilio_trial: boolean;
  ai_available: boolean;
  recent: CallRow[];
};

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<Overview>("/api/v1/overview")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <p className="text-[var(--danger)]">{err}</p>;
  if (!data) return <p className="text-[var(--muted)]">Loading overview...</p>;

  const cards = [
    { label: "Calls", value: data.calls_total },
    { label: "Blocked", value: data.calls_blocked },
    { label: "Contacts", value: data.contacts },
    { label: "Devices", value: data.devices },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-3xl">Overview</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Policy {data.policy_mode}. Give people the Haven number. Keep the iPhone number private.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{c.label}</p>
            <p className="display mt-2 text-3xl tabular-nums">{c.value}</p>
          </Card>
        ))}
      </div>
      <Card>
        <div className="flex flex-wrap gap-4">
          <StatusDot tone={data.twilio_ok ? "ok" : "warn"} label={data.twilio_ok ? "Twilio configured" : "Twilio missing"} />
          <StatusDot tone={data.twilio_trial ? "warn" : "ok"} label={data.twilio_trial ? "Trial (no forward/voicemail)" : "Upgraded Voice"} />
          <StatusDot tone={data.ai_available ? "ok" : "neutral"} label={data.ai_available ? "xAI ready" : "Rules only"} />
        </div>
        <p className="mt-4 text-sm text-[var(--muted)]">
          {data.twilio_phone
            ? `Haven number ${data.twilio_phone}. Unknown callers are challenged. Contacts forward to your iPhone after Twilio is upgraded.`
            : "Add a Twilio Voice number to start screening. This does not take over your existing iPhone line."}
        </p>
      </Card>
      <Card>
        <h2 className="display text-xl">Recent calls</h2>
        {data.recent.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--muted)]">No calls yet. Use Telephony to simulate one.</p>
        ) : (
          <ul className="mt-4 divide-y divide-[var(--line)]">
            {data.recent.map((c) => (
              <li key={c.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm">
                <span className="font-medium">{c.from_e164 || "anonymous"}</span>
                <span className="text-[var(--muted)]">{c.decision}</span>
                <span className="tabular-nums text-[var(--muted)]">{c.spam_score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
