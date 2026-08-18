# Security

- Argon2id passwords. TOTP required after first login. Recovery codes hashed.
- Passkeys via WebAuthn. RP ID is `HAVEN_DOMAIN`.
- HttpOnly cookies. Access 15 minutes, rotating refresh 14 days.
- CSRF: mutating `/api` checks Origin / Fetch-Site. Voice webhooks skip cookies and require Twilio signatures.
- Rate limits on login, TOTP, recovery.
- TOTP secrets encrypted with `HAVEN_DATA_KEY`.
- No analytics. No third-party scripts. Self-hosted Fontshare.
- UFW: 22, 80, 443. fail2ban on sshd is recommended.
- Containers drop capabilities. Recordings volume mode 700.
- Never commit `.env`. Run `scan-secrets-before-commit.ps1` before git commit.

Suggested fail2ban filter: jail on repeated 401s to `/api/v1/auth/login`.
