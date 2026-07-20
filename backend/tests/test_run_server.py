"""Tests for the packaged launcher, diagnostics, locking, and backups."""

import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from run_server import InstanceLock, collect_diagnostics, create_backup


def _write_manifest(root: Path, name: str = "asset.bin") -> None:
    root.mkdir(parents=True, exist_ok=True)
    asset = root / name
    asset.write_bytes(b"verified release asset")
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    (root / "model_manifest.json").write_text(
        json.dumps({"files": {name: digest}}),
        encoding="utf-8",
    )


def test_instance_lock_rejects_a_second_launcher(tmp_path):
    lock_path = tmp_path / "server.lock"
    first = InstanceLock(lock_path)
    second = InstanceLock(lock_path)

    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()
    assert not lock_path.exists()
    assert second.acquire() is True
    second.release()


def test_backup_uses_sqlite_backup_and_preserves_configuration(monkeypatch, tmp_path):
    database = tmp_path / "state" / "scan_history.db"
    config = tmp_path / "state" / "config" / ".env"
    backup_dir = tmp_path / "state" / "backups"
    database.parent.mkdir(parents=True)
    config.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('history-preserved')")
    config.write_text("DELETE_API_KEY=private-backup-value\n", encoding="utf-8")

    monkeypatch.setenv("EWASTE_DB_PATH", str(database))
    monkeypatch.setenv("EWASTE_CONFIG_PATH", str(config))
    monkeypatch.setenv("EWASTE_BACKUP_DIR", str(backup_dir))
    monkeypatch.setenv("EWASTE_LOG_DIR", str(tmp_path / "state" / "logs"))
    destination = create_backup()

    assert destination.parent == backup_dir
    with zipfile.ZipFile(destination) as archive:
        assert set(archive.namelist()) == {
            "backup_manifest.json",
            "config/.env",
            "data/scan_history.db",
        }
        assert archive.read("config/.env") == b"DELETE_API_KEY=private-backup-value\n"
        archive.extract("data/scan_history.db", tmp_path / "restored")
    with sqlite3.connect(tmp_path / "restored" / "data" / "scan_history.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "history-preserved"


def test_doctor_validates_assets_without_exposing_secrets(monkeypatch, tmp_path):
    frontend = tmp_path / "bundle" / "frontend"
    classifier = tmp_path / "bundle" / "classifier"
    lifespan = tmp_path / "bundle" / "lifespan"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    _write_manifest(classifier)
    _write_manifest(lifespan)

    monkeypatch.setenv("EWASTE_DATA_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EWASTE_DB_PATH", str(tmp_path / "state" / "data" / "doctor.db"))
    monkeypatch.setenv("EWASTE_FRONTEND_DIR", str(frontend))
    monkeypatch.setenv("EWASTE_CLASSIFIER_MODEL_PATH", str(classifier))
    monkeypatch.setenv("EWASTE_LIFESPAN_MODEL_DIR", str(lifespan))
    monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", "pk_test_doctor")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )
    monkeypatch.setenv("DELETE_API_KEY", "must-never-appear")

    report = collect_diagnostics(port=49152)
    serialized = json.dumps(report)

    assert report["status"] == "ready"
    assert all(item["ready"] for item in report["components"].values())
    assert "must-never-appear" not in serialized
    assert "pk_test_doctor" not in serialized
