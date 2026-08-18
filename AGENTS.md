# HavenID folder rules

Self-hosted personal identity + phone hub. Single-user. MIT public source.

## Product

- Canonical tree: this folder only.
- Contacts, recordings, and account data stay on machines the operator controls.
- Public GitHub: `Pitchfork-and-Torch/HavenID` (MIT).
- Parked for production webhook/VPS until you choose to deploy. See `docs/PARKED.md`.
- Product bet: published screening number, not CallKit hijack of the iPhone line. `docs/PRODUCT.md`.
- Not AetherOS, not SafeDeposit, not a Telegram phone-ops bot.

## Stack

- API: FastAPI (`apps/api`)
- Web: Next.js App Router (`apps/web`)
- Postgres + Redis + Caddy in Docker Compose
- Same origin: `/` web, `/api` `/voice` `/ws` API

## Hard rules

- No secrets in git. Commit `.env.example` only.
- No analytics, no third-party tracking JS.
- Fontshare only (Satoshi + Clash Display). No Inter.
- EN-only until the operator lifts the i18n hold.
- ASCII punctuation in docs and UI copy (hyphen or comma, not em dash).
- Recording and AI transcription stay off until the UI legal toggle is set.
- Twilio webhooks must verify `X-Twilio-Signature`.
- Trial Twilio cannot `<Dial><Number>` or `<Record>`. Use the simulator and trial-aware flags.
- Do not deploy onto a production host unless you explicitly choose to.
- Run `scan-secrets-before-commit.ps1` before any commit.
- Desk-claim this tree before editing from another session.

## Local servers (Grok TUI - non-negotiable)

`uvicorn`, `npm run dev`, and `next dev` never exit. Grok wraps every command in a Windows Job Object. `Start-Process` children stay in that job, so the TUI row never completes and timeout / `[stop]` kills the server. `Invoke-RestMethod` can also hang for minutes on WPAD/proxy even with `-TimeoutSec`.

**Banned as a Grok command (foreground or `background: true`):**
`py -3 -m uvicorn ...`, `npm run dev`, `npx next`, `next dev`.

**Only legal start / probe:**

```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\start-api.ps1
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\start-web.ps1
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\probe-api.ps1
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\HavenID\scripts\probe-web.ps1
```

Those scripts spawn **outside** the TUI job (explorer parent-spoof, then WMI, then schtasks) and **refuse** a child that is still in a job. They do **not** wait for HTTP. Cap is 8s, then `HARD_DEADLINE`. `CREATE_BREAKAWAY_FROM_JOB` is not a fix (2026-08-16 afternoon hang).

- Already-up is success (`ALREADY_UP`).
- After start, probe is a **separate** short command. Never `get_command_or_subagent_output` on a server.
- Stop: `scripts\stop-api.ps1` / `scripts\stop-web.ps1`.
- If a TUI row is already stuck: operator **Ctrl+B**. Do **not** `[stop]` if the API/web should stay up.
- Skill: `havenid-local-stack`.

## Conventions

- E.164 for every phone number in storage.
- Alembic for schema changes (`apps/api/alembic`).
- Pipeline decisions live in `app/pipeline/engine.py` (pure + tested).
- `TelephonyProvider` for Twilio now, SIP later.
- Tests: `cd apps/api; py -3 -m pytest`
