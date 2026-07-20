"""Frozen/local launcher for the single-origin E-Waste Management application."""

from __future__ import annotations

import argparse
from contextlib import suppress
from datetime import datetime, timezone
import json
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import socket
import sqlite3
import sys
import tempfile
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import webbrowser
import zipfile

from app import runtime

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
READINESS_TIMEOUT_SECONDS = 300


class InstanceLock:
    """Cross-platform, process-scoped lock used to prevent two local servers."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.handle = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"\0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError):
            self.handle.close()
            self.handle = None
            return False

        self.handle.seek(1)
        self.handle.truncate()
        self.handle.write(str(os.getpid()).encode("ascii"))
        self.handle.flush()
        return True

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None
            with suppress(OSError):
                self.path.unlink()

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("E-Waste Management is already running")
        return self

    def __exit__(self, *_args) -> None:
        self.release()


def _http_json(url: str, timeout: float = 1.5) -> tuple[int | None, dict[str, Any] | None]:
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload if isinstance(payload, dict) else None
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (OSError, ValueError, UnicodeError):
            payload = None
        return exc.code, payload if isinstance(payload, dict) else None
    except (OSError, URLError, ValueError, UnicodeError):
        return None, None


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((LOOPBACK_HOST, port))
        except OSError:
            return False
    return True


def _port_diagnostic(port: int) -> dict[str, Any]:
    status, payload = _http_json(f"http://{LOOPBACK_HOST}:{port}/health/live")
    if status == 200 and payload and payload.get("engine") == "E-Waste Management v3":
        return {"ready": True, "state": "application_running", "port": port}
    available = _port_available(port)
    return {
        "ready": available,
        "state": "available" if available else "occupied_by_another_process",
        "port": port,
    }


def _directory_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, prefix=".write-test-", delete=True):
            pass
        return True
    except OSError:
        return False


def collect_diagnostics(port: int = DEFAULT_PORT) -> dict[str, Any]:
    """Run non-secret, non-inference checks for packaged release prerequisites."""
    runtime.ensure_runtime_directories()
    runtime.load_runtime_environment()

    from app.db import database_healthcheck, init_db
    from app.model import DEFAULT_MODEL

    config = runtime.public_runtime_config()
    config_warnings = []
    if os.getenv("DELETE_API_KEY"):
        config_warnings.append(
            "DELETE_API_KEY is set; the browser UI intentionally cannot send this secret, so history deletion will be unavailable"
        )
    frontend = runtime.frontend_dist_path()
    classifier = runtime.classifier_model_path(DEFAULT_MODEL)
    lifespan = runtime.lifespan_model_path()

    try:
        init_db()
        db_ready, db_error = database_healthcheck()
    except (OSError, sqlite3.Error):
        db_ready, db_error = False, "database unavailable"

    if classifier is None:
        classifier_ready, classifier_errors = False, ["packaged classifier path is not selected"]
    else:
        classifier_ready, classifier_errors = runtime.verify_file_manifest(classifier)
    lifespan_ready, lifespan_errors = runtime.verify_file_manifest(lifespan)

    machine = platform.machine().casefold()
    packaged_platform_ready = not runtime.is_frozen() or (
        runtime.is_windows() and machine in {"amd64", "x86_64"}
    )
    writable = all(
        _directory_writable(path)
        for path in (
            runtime.database_path().parent,
            runtime.log_directory(),
            runtime.backup_directory(),
            runtime.config_path().parent,
        )
    )

    components = {
        "platform": {
            "ready": packaged_platform_ready,
            "system": platform.system(),
            "architecture": platform.machine(),
            "packaged": runtime.is_frozen(),
        },
        "configuration": {
            "ready": config["configured"],
            "exists": runtime.config_path().is_file(),
            "errors": config["errors"],
            "warnings": config_warnings,
        },
        "writable_state": {"ready": writable, "root": str(runtime.app_data_root())},
        "database": {"ready": db_ready, "error": db_error},
        "frontend": {
            "ready": (frontend / "index.html").is_file(),
            "path": str(frontend),
        },
        "classifier": {
            "ready": classifier_ready,
            "preset": DEFAULT_MODEL,
            "errors": classifier_errors,
        },
        "lifespan_models": {"ready": lifespan_ready, "errors": lifespan_errors},
        "port": _port_diagnostic(port),
    }
    return {
        "application": "E-Waste Management",
        "version": runtime.APP_VERSION,
        "status": "ready" if all(item["ready"] for item in components.values()) else "not_ready",
        "components": components,
    }


def _print_diagnostics(report: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(f"E-Waste Management {report['version']} diagnostics")
    print(f"Overall: {report['status'].upper()}")
    for name, component in report["components"].items():
        marker = "OK" if component["ready"] else "FAIL"
        print(f"  [{marker}] {name.replace('_', ' ')}")
        for error in component.get("errors") or []:
            print(f"         - {error}")
        for warning in component.get("warnings") or []:
            print(f"         - WARNING: {warning}")
        if component.get("error"):
            print(f"         - {component['error']}")
        if name == "port":
            print(f"         - {component['state']} on {LOOPBACK_HOST}:{component['port']}")


def run_doctor(port: int, as_json: bool) -> int:
    report = collect_diagnostics(port)
    _print_diagnostics(report, as_json)
    return 0 if report["status"] == "ready" else 2


def _wait_and_open_browser(port: int, timeout: int = READINESS_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://{LOOPBACK_HOST}:{port}"
    while time.monotonic() < deadline:
        status, payload = _http_json(f"{url}/health/ready", timeout=2.0)
        if status == 200 and payload and payload.get("status") == "ready":
            webbrowser.open(url, new=2)
            return
        time.sleep(0.75)
    print(
        "The browser was not opened because readiness did not succeed. "
        "Run Diagnose E-Waste.cmd for details.",
        file=sys.stderr,
    )


def run_server(port: int, open_browser: bool) -> int:
    """Start one loopback-only Uvicorn process and optionally open its SPA."""
    runtime.ensure_runtime_directories()
    runtime.load_runtime_environment()
    if runtime.is_frozen():
        os.environ["EWASTE_REQUIRE_FRONTEND"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"

    lock = InstanceLock(runtime.app_data_root() / "server.lock")
    if not lock.acquire():
        print(
            f"E-Waste Management is already running. Open http://{LOOPBACK_HOST}:{port}",
            file=sys.stderr,
        )
        return 3
    try:
        if not _port_available(port):
            status, payload = _http_json(f"http://{LOOPBACK_HOST}:{port}/health/live")
            if status == 200 and payload and payload.get("engine") == "E-Waste Management v3":
                print(f"E-Waste Management is already available at http://{LOOPBACK_HOST}:{port}")
                return 3
            print(
                f"Port {port} is occupied by another process. Run diagnostics or select another port.",
                file=sys.stderr,
            )
            return 4

        from app.main import create_app
        import uvicorn

        application = create_app(require_frontend=runtime.is_frozen(), enable_model_warmup=True)
        if open_browser:
            threading.Thread(
                target=_wait_and_open_browser,
                args=(port,),
                name="readiness-browser",
                daemon=True,
            ).start()

        print(f"Starting E-Waste Management at http://{LOOPBACK_HOST}:{port}")
        uvicorn.run(
            application,
            host=LOOPBACK_HOST,
            port=port,
            log_level=os.getenv("LOG_LEVEL", "info").casefold(),
            access_log=True,
        )
        return 0
    finally:
        lock.release()


def create_backup(output: Path | None = None) -> Path:
    """Create a consistent SQLite/config ZIP without stopping the application."""
    runtime.ensure_runtime_directories()
    runtime.load_runtime_environment()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(output) if output else (
        runtime.backup_directory() / f"EWasteManagement-backup-{timestamp}.zip"
    )
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")

    with tempfile.TemporaryDirectory(prefix="ewaste-backup-") as temporary:
        staging = Path(temporary)
        files: list[str] = []
        source_db = runtime.database_path()
        if source_db.is_file():
            backup_db = staging / "data" / "scan_history.db"
            backup_db.parent.mkdir(parents=True)
            with sqlite3.connect(source_db) as source, sqlite3.connect(backup_db) as target:
                source.backup(target)
            files.append("data/scan_history.db")

        source_config = runtime.config_path()
        if source_config.is_file():
            backup_config = staging / "config" / ".env"
            backup_config.parent.mkdir(parents=True)
            shutil.copy2(source_config, backup_config)
            files.append("config/.env")

        manifest = {
            "application": "E-Waste Management",
            "version": runtime.APP_VERSION,
            "createdUtc": datetime.now(timezone.utc).isoformat(),
            "files": files,
        }
        (staging / "backup_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_zip = destination.with_suffix(destination.suffix + ".tmp")
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for candidate in sorted(staging.rglob("*")):
                if candidate.is_file():
                    archive.write(candidate, candidate.relative_to(staging).as_posix())
        temporary_zip.replace(destination)
    return destination


def _valid_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("serve", "doctor", "backup"), default="serve")
    parser.add_argument("--doctor", action="store_true", help="Alias for the doctor command")
    parser.add_argument("--port", type=_valid_port, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser after readiness")
    parser.add_argument("--json", action="store_true", help="Print doctor output as JSON")
    parser.add_argument("--output", type=Path, help="Explicit backup ZIP destination")
    parser.add_argument("--version", action="version", version=runtime.APP_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = build_parser().parse_args(argv)
    command = "doctor" if args.doctor else args.command
    if command == "doctor":
        return run_doctor(args.port, args.json)
    if command == "backup":
        try:
            destination = create_backup(args.output)
        except (OSError, sqlite3.Error) as exc:
            print(f"Backup failed: {exc}", file=sys.stderr)
            return 5
        print(f"Backup created: {destination}")
        return 0
    return run_server(args.port, not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
