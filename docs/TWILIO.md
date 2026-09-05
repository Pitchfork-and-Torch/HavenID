# Twilio

HavenID talks to Twilio over signed webhooks. Put credentials in local `.env`
(never commit them). See `.env.example`.

## Trial vs upgraded

Trial Voice cannot use `<Dial><Number>` or `<Record>`. Forwarding and
voicemail stay disabled while `TWILIO_TRIAL=true`.

On a full account, set `TWILIO_TRIAL=false`. Forwarding works once VoiceUrl
points at your Haven origin and Telephony Forward-to is set.

## Connect a number

1. Buy or reuse a Twilio number with Voice + SMS.
2. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER`
   in `.env` (E.164).
3. Point VoiceUrl at `https://YOUR_DOMAIN/voice/inbound` and StatusCallback
   at `/voice/status` (or run `scripts/twilio-configure.sh`).
4. Set Telephony Forward-to to the handset that should ring after a pass.

Do not put a real personal number, account SID, or auth token in this repo.

## Test without minutes

Sign in, open Telephony, Simulate inbound. That writes a real call log and
returns TwiML.

## 10DLC (US SMS)

Bulk US SMS needs a brand + campaign in the Twilio Console. Voice screening
does not. Keep Console leftovers (domain verify, brand status) out of git.
