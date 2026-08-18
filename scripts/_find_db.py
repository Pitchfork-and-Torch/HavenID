"""Throwaway DB locator. Prints counts only, never emails."""
from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
cands = [
    root / "apps" / "api" / "havenid.db",
    root / "havenid.db",
]
for p in cands:
    print("---", p, "exists", p.exists(), "size", p.stat().st_size if p.exists() else 0)
    if not p.exists():
        continue
    cx = sqlite3.connect(p)
    tables = [r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1")]
    print("tables", tables)
    if "users" in tables:
        n = cx.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        totp = cx.execute("SELECT COUNT(*) FROM users WHERE totp_confirmed_at IS NOT NULL").fetchone()[0]
        print("users", n, "totp_enrolled", totp)
    cx.close()
