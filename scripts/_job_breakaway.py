#!/usr/bin/env python3
"""Spawn a process that is not in the current Windows Job Object.

Some agent shells wrap each command in a Job Object and wait until that job
is empty. CREATE_BREAKAWAY_FROM_JOB can return success while the child stays
in the job. A live server left in the job hangs the parent until the job is
killed, which also kills the server.

Never return a pid that is still in a job when this process is in a job.
Prefer parent-spoof (explorer), then WMI, then a one-shot scheduled task.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
import uuid
from ctypes import wintypes
from pathlib import Path

CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
PROC_THREAD_ATTRIBUTE_PARENT_PROCESS = 0x00020000
STARTF_USESTDHANDLES = 0x00000100
STARTF_USESHOWWINDOW = 0x00000001
SW_HIDE = 0
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
STILL_ACTIVE = 259
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
PROCESS_CREATE_PROCESS = 0x0080
PROCESS_DUP_HANDLE = 0x0040
TH32CS_SNAPPROCESS = 0x00000002

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
SIZE_T = ctypes.c_size_t
INVALID_HANDLE = wintypes.HANDLE(-1).value


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.TerminateProcess.restype = wintypes.BOOL
kernel32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
kernel32.IsProcessInJob.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(SIZE_T),
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    SIZE_T,
    ctypes.c_void_p,
    SIZE_T,
    ctypes.c_void_p,
    ctypes.POINTER(SIZE_T),
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
user32.GetShellWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD


def _sa_inherit() -> SECURITY_ATTRIBUTES:
    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    sa.lpSecurityDescriptor = None
    sa.bInheritHandle = True
    return sa


def _create_file(path: str, write: bool) -> int:
    sa = _sa_inherit()
    access = GENERIC_WRITE if write else GENERIC_READ
    disp = CREATE_ALWAYS if write else OPEN_EXISTING
    handle = kernel32.CreateFileW(
        path,
        access,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        ctypes.byref(sa),
        disp,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE or not handle:
        raise OSError(ctypes.get_last_error(), f"CreateFileW failed for {path}")
    return handle


def process_alive(pid: int) -> bool:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def in_any_job(pid: int | None = None) -> bool | None:
    if pid is None:
        handle = kernel32.GetCurrentProcess()
        own = True
    else:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        own = False
        if not handle:
            return None
    try:
        flag = wintypes.BOOL()
        if not kernel32.IsProcessInJob(handle, None, ctypes.byref(flag)):
            return None
        return bool(flag.value)
    finally:
        if not own:
            kernel32.CloseHandle(handle)


def terminate_pid(pid: int) -> None:
    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not handle:
        return
    try:
        kernel32.TerminateProcess(handle, 1)
    finally:
        kernel32.CloseHandle(handle)


def _close_pi(pi: PROCESS_INFORMATION) -> None:
    if pi.hThread:
        kernel32.CloseHandle(pi.hThread)
    if pi.hProcess:
        kernel32.CloseHandle(pi.hProcess)


def _create_plain(argv: list[str], cwd: str, out_path: str | None, err_path: str | None) -> tuple[int | None, str]:
    h_out = h_err = h_in = None
    try:
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.dwFlags = STARTF_USESHOWWINDOW
        si.wShowWindow = SW_HIDE
        inherit = False
        if out_path and err_path:
            h_out = _create_file(out_path, True)
            h_err = _create_file(err_path, True)
            h_in = _create_file("NUL", False)
            si.dwFlags |= STARTF_USESTDHANDLES
            si.hStdInput = h_in
            si.hStdOutput = h_out
            si.hStdError = h_err
            inherit = True
        pi = PROCESS_INFORMATION()
        cmd_buf = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        flags = CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT
        ok = kernel32.CreateProcessW(
            argv[0],
            cmd_buf,
            None,
            None,
            inherit,
            flags,
            None,
            cwd,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            return None, f"CreateProcessW last_error={ctypes.get_last_error()}"
        pid = int(pi.dwProcessId)
        _close_pi(pi)
        return pid, "plain"
    except OSError as exc:
        return None, str(exc)
    finally:
        for handle in (h_out, h_err, h_in):
            if handle:
                kernel32.CloseHandle(handle)


def _create_with_parent(argv: list[str], cwd: str, parent_pid: int) -> tuple[int | None, str]:
    access = PROCESS_CREATE_PROCESS | PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_DUP_HANDLE
    h_parent = kernel32.OpenProcess(access, False, int(parent_pid))
    if not h_parent:
        return None, f"OpenProcess parent last_error={ctypes.get_last_error()}"
    attr = None
    try:
        size = SIZE_T(0)
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        attr = ctypes.create_string_buffer(size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr, 1, 0, ctypes.byref(size)):
            return None, f"InitAttr last_error={ctypes.get_last_error()}"
        parent_handle = wintypes.HANDLE(h_parent)
        if not kernel32.UpdateProcThreadAttribute(
            attr,
            0,
            PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
            ctypes.byref(parent_handle),
            ctypes.sizeof(parent_handle),
            None,
            None,
        ):
            return None, f"UpdateAttr last_error={ctypes.get_last_error()}"
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
        si.StartupInfo.dwFlags = STARTF_USESHOWWINDOW
        si.StartupInfo.wShowWindow = SW_HIDE
        si.lpAttributeList = ctypes.cast(attr, ctypes.c_void_p)
        pi = PROCESS_INFORMATION()
        cmd_buf = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        flags = (
            CREATE_NEW_PROCESS_GROUP
            | CREATE_NO_WINDOW
            | CREATE_UNICODE_ENVIRONMENT
            | EXTENDED_STARTUPINFO_PRESENT
        )
        ok = kernel32.CreateProcessW(
            argv[0],
            cmd_buf,
            None,
            None,
            False,
            flags,
            None,
            cwd,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ok:
            return None, f"CreateProcessW parent-spoof last_error={ctypes.get_last_error()}"
        pid = int(pi.dwProcessId)
        _close_pi(pi)
        return pid, f"parent-{parent_pid}"
    except OSError as exc:
        return None, str(exc)
    finally:
        if attr is not None:
            try:
                kernel32.DeleteProcThreadAttributeList(attr)
            except Exception:
                pass
        kernel32.CloseHandle(h_parent)


def _pids_named(exe_name: str) -> list[int]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE or not snap:
        return []
    out: list[int] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return []
        target = exe_name.lower()
        while True:
            if entry.szExeFile.lower() == target:
                out.append(int(entry.th32ProcessID))
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
        return out
    finally:
        kernel32.CloseHandle(snap)


def _shell_pid() -> int | None:
    hwnd = user32.GetShellWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value) or None


def _out_of_job_parent() -> int | None:
    seen: list[int] = []
    shell = _shell_pid()
    if shell:
        seen.append(shell)
    for name in ("explorer.exe", "sihost.exe", "RuntimeBroker.exe"):
        seen.extend(_pids_named(name))
    checked: set[int] = set()
    for pid in seen:
        if pid in checked or pid <= 0:
            continue
        checked.add(pid)
        if in_any_job(pid) is False:
            return pid
    return None


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _wmi_create(argv: list[str], cwd: str) -> tuple[int | None, str]:
    inner = subprocess.list2cmdline(argv)
    script = (
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        "-Arguments @{ CommandLine = "
        + _ps_quote(inner)
        + "; CurrentDirectory = "
        + _ps_quote(cwd)
        + " }; "
        "if ($null -eq $r) { Write-Output 'RV=-1'; Write-Output 'PID='; exit 1 }; "
        "Write-Output ('RV=' + $r.ReturnValue); "
        "Write-Output ('PID=' + $r.ProcessId)"
    )
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
    except Exception as exc:
        return None, f"wmi_invoke:{type(exc).__name__}:{exc}"
    rv = None
    pid = None
    for line in (completed.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("RV="):
            try:
                rv = int(line[3:])
            except ValueError:
                rv = -1
        if line.startswith("PID=") and line[4:].isdigit():
            pid = int(line[4:])
    if completed.returncode != 0 or rv not in (0, None) or not pid:
        err = (completed.stderr or completed.stdout or "").strip()
        return None, f"wmi_rv={rv} rc={completed.returncode} {err[:200]}"
    return pid, "wmi"


def _schtasks_run(cmd_path: str) -> tuple[bool, str]:
    name = f"Knock-HavenID-spawn-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    create = subprocess.run(
        [
            "schtasks.exe",
            "/Create",
            "/TN",
            name,
            "/TR",
            cmd_path,
            "/SC",
            "ONCE",
            "/ST",
            "23:59",
            "/F",
            "/RL",
            "LIMITED",
        ],
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    if create.returncode != 0:
        err = (create.stderr or create.stdout or "").strip()
        return False, f"schtasks_create rc={create.returncode} {err[:200]}"
    try:
        run = subprocess.run(
            ["schtasks.exe", "/Run", "/TN", name],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if run.returncode != 0:
            err = (run.stderr or run.stdout or "").strip()
            return False, f"schtasks_run rc={run.returncode} {err[:200]}"
        return True, "schtasks"
    finally:
        subprocess.run(
            ["schtasks.exe", "/Delete", "/TN", name, "/F"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )


def _write_cmd(path: Path, argv: list[str]) -> None:
    lines = ["@echo off", "setlocal", subprocess.list2cmdline(argv)]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def _wait_pid_file(pid_file: Path, timeout: float = 3.0) -> int | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            raw = pid_file.read_text(encoding="ascii", errors="replace").strip()
        except OSError:
            raw = ""
        if raw.isdigit():
            pid = int(raw)
            if process_alive(pid):
                return pid
        time.sleep(0.05)
    return None


def _helper_argv(cwd: str, out_path: str, err_path: str, pid_file: Path, argv: list[str]) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "supervise",
        "--cwd",
        cwd,
        "--out",
        out_path,
        "--err",
        err_path,
        "--pid-file",
        str(pid_file),
        "--",
        *argv,
    ]


def _accept_child(pid: int, method: str) -> tuple[int, str] | tuple[None, str]:
    if not process_alive(pid):
        return None, f"{method} child died immediately"
    self_job = in_any_job()
    child_job = in_any_job(pid)
    if self_job and child_job:
        terminate_pid(pid)
        return None, f"{method} child still in a job (refused)"
    return pid, method


def spawn(argv: list[str], cwd: str, out_path: str, err_path: str) -> tuple[int, str]:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(err_path).parent.mkdir(parents=True, exist_ok=True)
    pid_file = Path(out_path).parent / f"spawned-{os.getpid()}.pid"
    if pid_file.exists():
        try:
            pid_file.unlink()
        except OSError:
            pass

    errors: list[str] = []
    if in_any_job() is not True:
        pid, method = _create_plain(argv, cwd, out_path, err_path)
        if pid:
            accepted, detail = _accept_child(pid, method)
            if accepted:
                return accepted, detail
            errors.append(detail)
        else:
            errors.append(method)
        raise RuntimeError("plain spawn failed: " + " | ".join(errors))

    helper = _helper_argv(cwd, out_path, err_path, pid_file, argv)

    parent = _out_of_job_parent()
    if parent:
        pid, method = _create_with_parent(helper, cwd, parent)
        if pid:
            server = _wait_pid_file(pid_file, 3.0)
            if server:
                accepted, detail = _accept_child(server, f"parent-{parent}")
                if accepted:
                    return accepted, detail
                errors.append(detail)
            else:
                terminate_pid(pid)
                errors.append(f"{method} no server pid file")
        else:
            errors.append(method)
    else:
        errors.append("no out-of-job parent")

    pid, method = _wmi_create(helper, cwd)
    if pid:
        server = _wait_pid_file(pid_file, 3.0)
        if server:
            accepted, detail = _accept_child(server, "wmi")
            if accepted:
                return accepted, detail
            errors.append(detail)
        else:
            terminate_pid(pid)
            errors.append("wmi no server pid file")
    else:
        errors.append(method)

    cmd_path = Path(out_path).parent / f"spawn-{os.getpid()}.cmd"
    _write_cmd(cmd_path, helper)
    ok, method = _schtasks_run(str(cmd_path))
    if ok:
        server = _wait_pid_file(pid_file, 3.0)
        if server:
            accepted, detail = _accept_child(server, "schtasks")
            if accepted:
                return accepted, detail
            errors.append(detail)
        else:
            errors.append("schtasks no server pid file")
    else:
        errors.append(method)

    raise RuntimeError("job escape failed: " + " | ".join(errors))


def supervise(argv: list[str], cwd: str, out_path: str, err_path: str, pid_file: str) -> int:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(err_path).parent.mkdir(parents=True, exist_ok=True)
    pid, method = _create_plain(argv, cwd, out_path, err_path)
    if not pid:
        Path(pid_file).write_text("0\n", encoding="ascii")
        sys.stderr.write(f"supervise spawn failed: {method}\n")
        return 1
    Path(pid_file).write_text(str(pid) + "\n", encoding="ascii")
    return 0


def diagnose() -> int:
    self_job = in_any_job()
    print(f"DIAG self_pid={os.getpid()} self_in_job={self_job}")
    parent = _out_of_job_parent()
    print(f"DIAG out_of_job_parent={parent}")
    if parent is not None:
        print(f"DIAG parent_in_job={in_any_job(parent)}")
    return 0


def selftest() -> int:
    def _boom() -> None:
        time.sleep(10)
        try:
            sys.stderr.write("SELFTEST_HARD_DEADLINE\n")
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(1)

    import threading

    threading.Thread(target=_boom, daemon=True).start()
    here = Path(__file__).resolve().parent
    run = here / ".breakaway-selftest"
    run.mkdir(exist_ok=True)
    out_path = str(run / "out.log")
    err_path = str(run / "err.log")
    argv = [sys.executable, "-c", "import time; time.sleep(30)"]
    pid = None
    try:
        pid, method = spawn(argv, str(here), out_path, err_path)
        time.sleep(0.2)
        alive = process_alive(pid)
        child_job = in_any_job(pid)
        self_job = in_any_job()
        print(f"SELFTEST method={method} pid={pid} alive={alive} self_in_job={self_job} child_in_job={child_job}")
        if not alive:
            print("SELFTEST_FAIL child died immediately")
            return 1
        if self_job and child_job:
            print("SELFTEST_FAIL child still in a job")
            return 1
        print("SELFTEST_OK")
        return 0
    except Exception as exc:
        print(f"SELFTEST_FAIL {exc}")
        return 1
    finally:
        if pid:
            terminate_pid(pid)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("spawn")
    sp.add_argument("--cwd", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--err", required=True)
    sp.add_argument("--pid-file")
    sp.add_argument("argv", nargs=argparse.REMAINDER)

    su = sub.add_parser("supervise")
    su.add_argument("--cwd", required=True)
    su.add_argument("--out", required=True)
    su.add_argument("--err", required=True)
    su.add_argument("--pid-file", required=True)
    su.add_argument("argv", nargs=argparse.REMAINDER)

    sub.add_parser("selftest")
    sub.add_parser("diagnose")
    args = ap.parse_args()

    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "diagnose":
        return diagnose()

    argv = list(args.argv)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print("missing command", file=sys.stderr)
        return 2

    if args.cmd == "supervise":
        return supervise(argv, args.cwd, args.out, args.err, args.pid_file)

    pid, method = spawn(argv, args.cwd, args.out, args.err)
    if args.pid_file:
        Path(args.pid_file).write_text(str(pid) + "\n", encoding="ascii")
    print(f"SPAWNED method={method} pid={pid} child_in_job={in_any_job(pid)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
