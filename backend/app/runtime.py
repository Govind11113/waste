"""Portable runtime paths and public configuration for source and packaged runs.

The Windows release treats its extracted program directory as immutable. All
mutable state is kept below ``%LOCALAPPDATA%\\EWasteManagement``. Source runs on
macOS/Linux retain the repository-local paths used by existing development
scripts unless an explicit environment override is provided.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
from typing import Mapping

APP_NAME = "EWasteManagement"
APP_VERSION = "3.0.0"
BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


def is_frozen() -> bool:
    """Return whether Python is running from a freezer such as PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def is_windows() -> bool:
    return os.name == "nt"


def bundle_root() -> Path:
    """Directory containing packaged runtime resources or the backend source."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return BACKEND_ROOT


def _env_path(name: str) -> Path | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return Path(os.path.expandvars(raw.strip())).expanduser().resolve()


def app_data_root() -> Path:
    override = _env_path("EWASTE_DATA_DIR")
    if override is not None:
        return override

    if is_windows() or is_frozen():
        local_app_data = os.getenv("LOCALAPPDATA")
        base = (
            Path(local_app_data).expanduser()
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base / APP_NAME

    # Preserve existing repository-local behavior for source development.
    return BACKEND_ROOT


def database_path() -> Path:
    override = _env_path("EWASTE_DB_PATH")
    if override is not None:
        return override
    if is_windows() or is_frozen():
        return app_data_root() / "data" / "scan_history.db"
    return BACKEND_ROOT / "scan_history.db"


def log_directory() -> Path:
    override = _env_path("EWASTE_LOG_DIR")
    if override is not None:
        return override
    if is_windows() or is_frozen():
        return app_data_root() / "logs"
    return BACKEND_ROOT / "logs"


def backup_directory() -> Path:
    override = _env_path("EWASTE_BACKUP_DIR")
    return override if override is not None else app_data_root() / "backups"


def config_path() -> Path:
    override = _env_path("EWASTE_CONFIG_PATH")
    if override is not None:
        return override
    if is_windows() or is_frozen():
        return app_data_root() / "config" / ".env"
    return BACKEND_ROOT / ".env"


def frontend_dist_path() -> Path:
    override = _env_path("EWASTE_FRONTEND_DIR")
    if override is not None:
        return override
    if is_frozen():
        return bundle_root() / "frontend"
    return PROJECT_ROOT / "frontend" / "dist"


def lifespan_model_path() -> Path:
    override = _env_path("EWASTE_LIFESPAN_MODEL_DIR")
    if override is not None:
        return override
    if is_frozen():
        return bundle_root() / "models" / "lifespan"
    return BACKEND_ROOT / "models" / "lifespan"


def classifier_model_path(preset_name: str) -> Path | None:
    """Return an explicit/bundled classifier path, or ``None`` for online dev."""
    override = _env_path("EWASTE_CLASSIFIER_MODEL_PATH")
    if override is not None:
        return override

    candidate = (
        bundle_root() / "models" / "classifier" / preset_name
        if is_frozen()
        else BACKEND_ROOT / "models" / "classifier" / preset_name
    )
    # A frozen application must fail clearly when its promised model is absent;
    # source development may continue using the configured Hugging Face model id.
    if is_frozen() or candidate.exists():
        return candidate
    return None


def ensure_runtime_directories() -> None:
    """Create only mutable directories, never resource/model directories."""
    database_path().parent.mkdir(parents=True, exist_ok=True)
    log_directory().mkdir(parents=True, exist_ok=True)
    backup_directory().mkdir(parents=True, exist_ok=True)
    config_path().parent.mkdir(parents=True, exist_ok=True)


def load_runtime_environment() -> Path | None:
    """Load the selected .env before modules read import-time configuration."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None

    selected = config_path()
    if selected.is_file():
        load_dotenv(selected, override=False)
        return selected

    # A packaged first run has no config yet; source runs may use backend/.env.
    source_env = BACKEND_ROOT / ".env"
    if not is_frozen() and source_env.is_file() and source_env != selected:
        load_dotenv(source_env, override=False)
        return source_env
    return None


def _looks_placeholder(value: str) -> bool:
    lowered = value.casefold()
    return any(token in lowered for token in ("example", "your-clerk", "replace-with"))


def public_runtime_config(env: Mapping[str, str] | None = None) -> dict:
    """Return the allowlisted browser configuration; never expose secrets."""
    values = os.environ if env is None else env
    publishable_key = (
        values.get("EWASTE_CLERK_PUBLISHABLE_KEY")
        or values.get("VITE_CLERK_PUBLISHABLE_KEY")
        or ""
    ).strip()
    jwks_url = (values.get("CLERK_JWKS_URL") or "").strip()

    errors: list[str] = []
    if not publishable_key:
        errors.append("Clerk publishable key is not configured")
    elif not publishable_key.startswith("pk_test_"):
        errors.append("Localhost requires a Clerk development publishable key (pk_test_)")
    elif _looks_placeholder(publishable_key):
        errors.append("Clerk publishable key is still a placeholder")

    if not jwks_url:
        errors.append("Clerk JWKS URL is not configured")
    elif not jwks_url.startswith("https://") or _looks_placeholder(jwks_url):
        errors.append("Clerk JWKS URL must be a real HTTPS development-instance URL")

    configured = not errors
    return {
        "version": APP_VERSION,
        "configured": configured,
        "clerkPublishableKey": publishable_key if configured else None,
        "apiBase": "/api/v1",
        "errors": errors,
    }


def verify_file_manifest(
    root: Path,
    manifest_name: str = "model_manifest.json",
) -> tuple[bool, list[str]]:
    """Verify wrapped or legacy-flat release asset SHA-256 manifests."""
    root = Path(root)
    manifest_path = root / manifest_name
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False, [f"missing or invalid manifest: {manifest_name}"]

    if isinstance(payload, dict) and isinstance(payload.get("files"), dict):
        files = payload["files"]
    elif isinstance(payload, dict):
        # Lifespan artifacts use the repository's legacy flat {path: sha256}
        # format; classifier release snapshots use {"files": {...}}.
        files = payload
    else:
        files = None
    if not isinstance(files, dict) or not files:
        return False, [f"manifest contains no files: {manifest_name}"]

    errors: list[str] = []
    resolved_root = root.resolve()
    for relative_name, expected in sorted(files.items()):
        if not isinstance(relative_name, str) or not isinstance(expected, str):
            errors.append("invalid manifest entry")
            continue
        candidate = (root / relative_name).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            errors.append(f"unsafe manifest path: {relative_name}")
            continue
        if not candidate.is_file():
            errors.append(f"missing file: {relative_name}")
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if not hmac.compare_digest(actual, expected.casefold()):
            errors.append(f"hash mismatch: {relative_name}")

    return not errors, errors
