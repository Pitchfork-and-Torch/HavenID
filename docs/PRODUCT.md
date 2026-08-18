# Product bet

HavenID is a personal screening number plus an identity dashboard. It is not a CallKit hook that hijacks the iPhone's existing cell number.

## Why this shape

Apple does not let a third-party app run a custom IVR on the user's real iPhone line. Call Directory can label or block numbers. Live Voicemail is Apple's. Neither lets you press-1, classify, or forward with your own rules.

A number the owner publishes does work today:

1. Friends and doctors call the Haven number (Twilio Voice).
2. Known contacts and allow-list numbers forward to the iPhone.
3. Unknown callers hear a short challenge (press 1) or get rejected.
4. The owner marks spam from the call log. That feeds the denylist.
5. Optional later: an iOS app for lists, notifications, and Call Directory labels on the real line.

Tell people the Haven number. Keep the iPhone number private. "Silence Unknown Callers" on the iPhone is complementary, not a competitor.

## What v1 must prove

- Login, TOTP, recovery, passkeys
- Contacts + allow/deny lists
- Simulator writes a real call log and honest TwiML
- Trial Twilio: challenge and reject only (no Dial, no Record)
- Upgraded Twilio: forward to the iPhone, optional voicemail after legal ack
- Works with no xAI key (rules + press-1)

## What v1 must not promise

- Filtering spam that still dials the existing cell number
- Carrier STIR/SHAKEN attestation
- SMS inbox
- A hosted multi-tenant SaaS (self-host first)

## License later

The tree stays proprietary while we see if this actually ends the spam-call mess.

If it works and the operator wants a public good: MIT, one-commit public repo, Pitchfork-and-Torch.

If it works and the operator wants to sell it: keep copyright, pick a commercial license, do not weaken Twilio/TCPA/recording rails to close a sale.

Do not create a GitHub repo until that choice is made.
