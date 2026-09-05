# API

Interactive docs: `/api/docs`  
OpenAPI: `/api/openapi.json`

All JSON routes sit under `/api/v1` and use cookie sessions (`credentials: include`).

Auth: `/auth/login`, `/auth/totp/*`, `/auth/refresh`, `/auth/logout`, `/auth/recover`, `/auth/webauthn/*`

Data: `/me`, `/me/export`, `/devices`, `/contacts`, `/calls`, `/lists`, `/policy`, `/settings`, `/overview`, `/audit`

Voice: `/voice/inbound`, `/voice/gather`, `/voice/status`, `/voice/recording` (Twilio signature)

Dev: `POST /api/v1/voice/simulate` (authenticated)
