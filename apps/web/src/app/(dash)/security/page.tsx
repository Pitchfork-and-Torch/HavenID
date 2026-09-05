"use client";

import { useEffect, useState } from "react";
import { Button, Card } from "@/components/ui";
import { api, type Me } from "@/lib/api";
import { b64ToBuf, bufferToB64 } from "@/lib/webauthn";

export default function SecurityPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [audit, setAudit] = useState<{ action: string; created_at: string | null; ip: string }[]>([]);

  useEffect(() => {
    api<Me>("/api/v1/me").then(setMe).catch(() => undefined);
    api<{ items: { action: string; created_at: string | null; ip: string }[] }>("/api/v1/audit")
      .then((r) => setAudit(r.items))
      .catch(() => undefined);
  }, []);

  async function registerPasskey() {
    const opts = await api<{ publicKey: Record<string, unknown> }>("/api/v1/auth/webauthn/register/options");
    const pk = opts.publicKey;
    const user = pk.user as { id: string; name: string; displayName: string };
    const publicKey: PublicKeyCredentialCreationOptions = {
      ...pk,
      challenge: b64ToBuf(String(pk.challenge)),
      user: { ...user, id: b64ToBuf(user.id) },
    } as PublicKeyCredentialCreationOptions;
    const cred = (await navigator.credentials.create({ publicKey })) as PublicKeyCredential;
    const att = cred.response as AuthenticatorAttestationResponse;
    await api("/api/v1/auth/webauthn/register", {
      method: "POST",
      body: JSON.stringify({
        id: cred.id,
        rawId: bufferToB64(cred.rawId),
        type: cred.type,
        response: {
          clientDataJSON: bufferToB64(att.clientDataJSON),
          attestationObject: bufferToB64(att.attestationObject),
        },
      }),
    });
    setMe(await api<Me>("/api/v1/me"));
  }

  return (
    <div className="space-y-6">
      <h1 className="display text-3xl">Security</h1>
      <Card>
        <p>TOTP: {me?.totp_enrolled ? "enrolled" : "required"}</p>
        <p className="mt-2">Passkeys: {me?.passkey_count ?? 0}</p>
        <Button className="mt-4" onClick={registerPasskey}>
          Add passkey
        </Button>
      </Card>
      <Card>
        <h2 className="display text-xl">Audit log</h2>
        <ul className="mt-3 max-h-96 space-y-2 overflow-auto text-sm">
          {audit.map((a, i) => (
            <li key={`${a.action}-${i}`} className="flex justify-between gap-3 border-b border-[var(--line)] py-2">
              <span>{a.action}</span>
              <span className="text-[var(--muted)]">
                {a.ip} {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
