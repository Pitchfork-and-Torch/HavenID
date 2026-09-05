"use client";

import { useEffect, useState } from "react";
import { Button, Card, Field, Input } from "@/components/ui";
import { api, type Me, type Policy } from "@/lib/api";

export default function TelephonyPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [forwards, setForwards] = useState("");
  const [simFrom, setSimFrom] = useState("+15551230000");
  const [twiml, setTwiml] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<Me>("/api/v1/me").then((m) => {
      setMe(m);
      setPolicy(m.policy);
      setForwards((m.policy?.forward_e164 || []).join(", "));
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!policy) return;
    const next = {
      ...policy,
      forward_e164: forwards
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    const saved = await api<Policy>("/api/v1/policy", { method: "PATCH", body: JSON.stringify(next) });
    setPolicy(saved);
    setMsg("Saved.");
  }

  async function simulate() {
    const r = await api<{ twiml: string }>("/api/v1/voice/simulate", {
      method: "POST",
      body: JSON.stringify({ frm: simFrom, stage: "inbound" }),
    });
    setTwiml(r.twiml);
  }

  if (!policy) return <p>Loading...</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="display text-3xl">Telephony</h1>
        <p className="text-sm text-[var(--muted)]">
          Publish the Haven number. Put your iPhone in Forward to. This is a screening line, not a hook on the cell number.
          {me?.twilio_phone ? ` Current Haven number: ${me.twilio_phone}.` : " No Twilio number configured yet."}{" "}
          {me?.twilio_trial ? "Trial mode: challenge and reject only. Upgrade Twilio to forward or record." : "Upgraded Voice: forward and voicemail available."}
        </p>
      </div>
      <Card>
        <form className="space-y-4" onSubmit={save}>
          <Field label="Policy mode">
            <select
              className="min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3"
              value={policy.mode}
              onChange={(e) => setPolicy({ ...policy, mode: e.target.value })}
            >
              <option value="strict">Strict</option>
              <option value="balanced">Balanced</option>
              <option value="permissive">Permissive</option>
            </select>
          </Field>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="checkbox" checked={policy.challenge_enabled} onChange={(e) => setPolicy({ ...policy, challenge_enabled: e.target.checked })} />
            Challenge unknown callers (press 1)
          </label>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="checkbox" checked={policy.ai_enabled} onChange={(e) => setPolicy({ ...policy, ai_enabled: e.target.checked })} />
            AI screen (needs xAI key and upgraded Twilio)
          </label>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={policy.record_voicemail}
              onChange={(e) => setPolicy({ ...policy, record_voicemail: e.target.checked })}
            />
            Voicemail recording
          </label>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={policy.recording_legal_ack}
              onChange={(e) => setPolicy({ ...policy, recording_legal_ack: e.target.checked })}
            />
            I am responsible for local call-recording and TCPA rules
          </label>
          <Field label="Forward to (comma-separated E.164)">
            <Input value={forwards} onChange={(e) => setForwards(e.target.value)} />
          </Field>
          <Field label="Ring">
            <select
              className="min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3"
              value={policy.ring_strategy}
              onChange={(e) => setPolicy({ ...policy, ring_strategy: e.target.value })}
            >
              <option value="simultaneous">Simultaneous</option>
              <option value="sequential">Sequential</option>
            </select>
          </Field>
          <Field label="Reject style">
            <select
              className="min-h-11 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3"
              value={policy.reject_style}
              onChange={(e) => setPolicy({ ...policy, reject_style: e.target.value })}
            >
              <option value="polite">Polite message</option>
              <option value="silent">Silent reject</option>
            </select>
          </Field>
          <Button type="submit">Save policy</Button>
          {msg ? <span className="ml-3 text-sm text-[var(--ok)]">{msg}</span> : null}
        </form>
      </Card>
      <Card>
        <h2 className="display text-xl">Simulate inbound</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Does not use Twilio minutes. Writes a real call log.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Input value={simFrom} onChange={(e) => setSimFrom(e.target.value)} />
          <Button onClick={simulate}>Run pipeline</Button>
        </div>
        {twiml ? <pre className="mt-4 overflow-auto rounded-lg bg-[var(--bg)] p-3 text-xs">{twiml}</pre> : null}
      </Card>
    </div>
  );
}
