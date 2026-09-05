# HavenID

Self-hosted personal identity and screening-number phone hub. Single-user. MIT.

Public GitHub: `Pitchfork-and-Torch/HavenID`.

## Product

- Canonical tree: this folder only.
- Contacts, recordings, and account data stay on machines you control.
- Parked for production webhook deploy until you choose to. See `docs/PARKED.md`.
- Product bet: published screening number, not CallKit hijack of the carrier line. `docs/PRODUCT.md`.

## Stack

- API: FastAPI (`apps/api`)
- Web: Next.js App Router (`apps/web`)
- Postgres + Redis + Caddy in Docker Compose
- Same origin: `/` web, `/api` `/voice` `/ws` API

## Hard rules

- No secrets in git. Commit `.env.example` only.
- No analytics, no third-party tracking JS.
- Fontshare only (Satoshi + Clash Display). No Inter.
- EN-only until i18n is explicitly resumed.
- ASCII punctuation in docs and UI copy (hyphen or comma, not em dash).
- Recording and AI transcription stay off until the UI legal toggle is set.
- Twilio webhooks must verify `X-Twilio-Signature`.
- Trial Twilio cannot `<Dial><Number>` or `<Record>`. Use the simulator and trial-aware flags.
- Do not deploy onto a production host unless you explicitly choose to.

## Local run

Docker Compose is the default.

On Windows, `scripts/start-api.ps1` and `scripts/start-web.ps1` start the API and web in detached processes so the start command can exit. They do not wait for health. Probe with `scripts/probe-api.ps1` and `scripts/probe-web.ps1`. Stop with `scripts/stop-api.ps1` and `scripts/stop-web.ps1`.

Do not run `uvicorn`, `npm run dev`, or `next dev` as a never-exit child of an agent job.

## Conventions

- E.164 for every phone number in storage.
- Alembic for schema changes (`apps/api/alembic`).
- Pipeline decisions live in `app/pipeline/engine.py` (pure + tested).
- `TelephonyProvider` for Twilio now, SIP later.
- Tests: `cd apps/api; py -3 -m pytest`
