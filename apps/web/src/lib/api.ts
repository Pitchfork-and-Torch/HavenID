export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    throw new ApiError(res.status, data.detail || res.statusText);
  }
  return data as T;
}

export type Me = {
  id: string;
  email: string;
  display_name: string;
  phone_e164: string | null;
  totp_enrolled: boolean;
  passkey_count: number;
  twilio_configured: boolean;
  twilio_phone: string;
  twilio_trial: boolean;
  ai_available: boolean;
  smtp_configured: boolean;
  policy: Policy | null;
  prefs: { notify_email_voicemail: boolean; notify_email_blocked: boolean; theme: string };
};

export type Policy = {
  mode: string;
  challenge_enabled: boolean;
  ai_enabled: boolean;
  record_voicemail: boolean;
  recording_legal_ack: boolean;
  ring_strategy: string;
  reject_style: string;
  forward_e164: string[];
  public_spam_lists: boolean;
};

export type Contact = {
  id: string;
  display_name: string;
  given_name: string;
  family_name: string;
  org: string;
  notes: string;
  phones: { id: string; e164: string; label: string; preferred: boolean }[];
  emails: { id: string; address: string; label: string }[];
};

export type CallRow = {
  id: string;
  from_e164: string | null;
  to_e164: string | null;
  started_at: string | null;
  duration_sec: number;
  outcome: string;
  decision: string;
  reason: string;
  spam_score: number;
  transcript: string;
};

export type ListRow = {
  id: string;
  list_kind: string;
  match_kind: string;
  pattern: string;
  note: string;
};
