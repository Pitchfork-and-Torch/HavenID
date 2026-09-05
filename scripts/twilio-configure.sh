#!/usr/bin/env bash
# Pin Voice webhooks on a Twilio number. Needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
# TWILIO_PHONE_NUMBER, HAVEN_PUBLIC_URL in the environment or ../.env
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
: "${TWILIO_ACCOUNT_SID:?}"
: "${TWILIO_AUTH_TOKEN:?}"
: "${TWILIO_PHONE_NUMBER:?}"
: "${HAVEN_PUBLIC_URL:?}"

BASE="${HAVEN_PUBLIC_URL%/}"
AUTH=(-u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN")
LIST=$(curl -fsS "${AUTH[@]}" "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/IncomingPhoneNumbers.json")
SID=$(python3 - <<PY
import json,sys,os
data=json.loads('''$LIST''')
want=os.environ["TWILIO_PHONE_NUMBER"].replace(" ","")
for n in data.get("incoming_phone_numbers",[]):
    if n.get("phone_number")==want:
        print(n["sid"]); break
PY
)
if [[ -z "$SID" ]]; then
  echo "Number $TWILIO_PHONE_NUMBER not found on this account."
  exit 1
fi
curl -fsS "${AUTH[@]}" -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/IncomingPhoneNumbers/$SID.json" \
  --data-urlencode "VoiceUrl=$BASE/voice/inbound" \
  --data-urlencode "VoiceMethod=POST" \
  --data-urlencode "StatusCallback=$BASE/voice/status" \
  --data-urlencode "StatusCallbackMethod=POST" >/dev/null
echo "Pinned VoiceUrl to $BASE/voice/inbound"
