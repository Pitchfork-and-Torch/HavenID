#!/usr/bin/env python3
"""Hard-timeout HTTP probe. No proxy. Must return quickly."""
from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


def tcp_open(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout):
            return True, "ok"
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def http_get(url: str, timeout: float) -> tuple[int | None, str, str]:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ok, err = tcp_open(host, port, min(0.5, timeout))
    if not ok:
        return None, "", err
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "havenid-probe/1"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(800).decode("utf-8", "replace")
            return int(resp.status), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read(800).decode("utf-8", "replace") if exc.fp else ""
        return int(exc.code), body, f"HTTPError:{exc}"
    except Exception as exc:
        return None, "", f"{type(exc).__name__}:{exc}"


def probe(url: str, timeout: float = 1.5, json_ok: bool = False) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    rec: dict = {"url": url, "up": False, "tcp": False}
    ok, err = tcp_open(host, port, min(0.5, timeout))
    rec["tcp"] = ok
    if not ok:
        rec["error"] = err
        return rec
    status, body, herr = http_get(url, timeout)
    rec["http"] = status
    rec["body"] = body[:240]
    if herr and status is None:
        rec["error"] = herr
        return rec
    if status is None or status >= 500:
        rec["error"] = herr or f"http_{status}"
        return rec
    if json_ok:
        try:
            data = json.loads(body)
        except Exception:
            rec["error"] = "not_json"
            return rec
        if not bool(data.get("ok")):
            rec["error"] = "json_ok_false"
            rec["json"] = data
            return rec
        rec["json"] = data
    rec["up"] = True
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--timeout", type=float, default=1.5)
    ap.add_argument("--json-ok", action="store_true")
    args = ap.parse_args()
    rec = probe(args.url, timeout=max(0.3, min(args.timeout, 5.0)), json_ok=args.json_ok)
    print(json.dumps(rec, separators=(",", ":")))
    return 0 if rec.get("up") else 1


if __name__ == "__main__":
    sys.exit(main())
