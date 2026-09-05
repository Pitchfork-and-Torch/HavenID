#!/usr/bin/env python3
"""Start HavenID api/web outside the current Windows Job Object, then exit.

This process must exit on a hard deadline. The server must not stay in this
process's job. Start does not wait for HTTP. Probe is a separate command.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path

from _http_probe import probe
from _job_breakaway import process_alive, spawn

ROOT = Path(__file__).resolve().parents[1]


def _hard_deadline(seconds: float) -> None:
    def _boom() -> None:
        time.sleep(seconds)
        try:
            sys.stderr.write("HARD_DEADLINE\n")
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(1)

    threading.Thread(target=_boom, daemon=True).start()


def _tail(path: Path, lines: int = 30) -> None:
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in text[-lines:]:
        print(line)


def _write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid) + "\n", encoding="ascii")


def _summarize(rec: dict) -> str:
    extra = ""
    data = rec.get("json") or {}
    if isinstance(data, dict):
        owner = data.get("has_owner")
        boot = data.get("bootstrap_configured")
        if owner is not None or boot is not None:
            extra = f" has_owner={owner} bootstrap_configured={boot}"
    return extra


def start_role(role: str, host: str, port: int, timeout: int) -> int:
    if role == "api":
        timeout = max(3, min(timeout, 8))
        cwd = ROOT / "apps" / "api"
        run = cwd / ".local-run"
        url = f"http://{host}:{port}/api/health"
        json_ok = True
        python = sys.executable
        argv = [python, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)]
        pid_file = run / "uvicorn.pid"
        out_log = run / "uvicorn.out.log"
        err_log = run / "uvicorn.err.log"
    elif role == "web":
        timeout = max(3, min(timeout, 8))
        cwd = ROOT / "apps" / "web"
        run = cwd / ".local-run"
        url = f"http://{host}:{port}/login"
        json_ok = False
        node = shutil.which("node.exe") or shutil.which("node")
        nxt = cwd / "node_modules" / "next" / "dist" / "bin" / "next"
        if not node:
            print("node not found")
            return 1
        if not nxt.is_file():
            print(f"next binary missing: {nxt}")
            return 1
        argv = [node, str(nxt), "dev", "-p", str(port), "-H", host]
        pid_file = run / "next.pid"
        out_log = run / "next.out.log"
        err_log = run / "next.err.log"
    else:
        print("role must be api or web")
        return 2

    _hard_deadline(timeout)
    rec = probe(url, timeout=1.2, json_ok=json_ok)
    if rec.get("up"):
        print(f"ALREADY_UP {url}{_summarize(rec)}")
        return 0

    if rec.get("tcp"):
        print(f"PORT_BUSY :{port} {url} not healthy error={rec.get('error')}")
        print("---- err log ----")
        _tail(err_log)
        return 1

    run.mkdir(parents=True, exist_ok=True)
    try:
        pid, method = spawn([str(a) for a in argv], str(cwd), str(out_log), str(err_log))
    except Exception as exc:
        print(f"SPAWN_FAIL {exc}")
        _tail(err_log, 40)
        return 1

    if not process_alive(pid):
        print(f"DIED pid={pid} see {err_log}")
        _tail(err_log, 40)
        return 1

    _write_pid(pid_file, pid)
    print(f"STARTED method={method} pid={pid} {url}")
    print("Spawned detached. Probe with probe-api.ps1 / probe-web.ps1. Do not wait here.")
    return 0


def probe_role(role: str, host: str, port: int) -> int:
    if role == "api":
        url = f"http://{host}:{port}/api/health"
        rec = probe(url, timeout=1.5, json_ok=True)
    else:
        url = f"http://{host}:{port}/login"
        rec = probe(url, timeout=1.5, json_ok=False)
    print(json.dumps(rec, separators=(",", ":")))
    return 0 if rec.get("up") else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["start", "probe"])
    ap.add_argument("role", choices=["api", "web"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=0)
    args = ap.parse_args()
    port = args.port or (8000 if args.role == "api" else 3000)
    timeout = args.timeout or 8
    if args.action == "probe":
        return probe_role(args.role, args.host, port)
    return start_role(args.role, args.host, port, timeout)


if __name__ == "__main__":
    sys.exit(main())
