"""Clear TOTP so the next browser login can enroll. Prints no secrets."""
from __future__ import annotations

import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "apps" / "api" / "havenid.db"
if not db.exists():
    raise SystemExit("FAIL no db")
cx = sqlite3.connect(db)
users = cx.execute("SELECT COUNT(*) FROM users").fetchone()[0]
if users < 1:
    raise SystemExit("FAIL no owner")
cx.execute("UPDATE users SET totp_secret_enc = NULL, totp_confirmed_at = NULL")
cx.execute("DELETE FROM recovery_codes")
cx.commit()
left = cx.execute("SELECT COUNT(*) FROM users WHERE totp_confirmed_at IS NOT NULL").fetchone()[0]
cx.close()
print("totp_reset", left == 0, "users", users)
