# Parked

Status: **local Twilio works**. Do not deploy a public webhook or VPS
origin until you choose to.

This is not a dead project. Do not rewrite it from scratch.

## Why it was parked

Local MVP is saved: owner bootstrap, login/TOTP smoke, screening-number
product bet, dashboard, simulator. Public webhook + production host still
wait on an explicit deploy.

## Resume

1. Read `docs/PRODUCT.md` (screening number, not CallKit intercept).
2. Start with the detached scripts. Do not run `uvicorn` or
   `npm run dev` as a never-exit child of an agent job. Prove with
   `selftest-breakaway.ps1`.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-api.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-web.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\probe-api.ps1
```

3. Login: `http://127.0.0.1:3000/login` with `BOOTSTRAP_*` from local `.env`
   (not in git).
4. First browser login enrolls TOTP. Save recovery codes.
5. Next product work is a public Haven URL (then pin VoiceUrl), plus
   Console 10DLC if you need bulk US SMS.

## License

MIT. Issues on this repo only. No personal contact.
