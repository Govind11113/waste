"""Regression tests for portable paths, runtime configuration, and SPA hosting."""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_windows_packaged_paths_use_local_app_data(monkeypatch, tmp_path):
    from app import runtime

    local_app_data = tmp_path / "Local App Data"
    bundle = tmp_path / "E-Waste Bundle"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.delenv("EWASTE_DATA_DIR", raising=False)
    monkeypatch.delenv("EWASTE_DB_PATH", raising=False)
    monkeypatch.delenv("EWASTE_LOG_DIR", raising=False)
    monkeypatch.setattr(runtime, "is_windows", lambda: True)
    monkeypatch.setattr(runtime, "is_frozen", lambda: True)
    monkeypatch.setattr(runtime, "bundle_root", lambda: bundle)

    assert runtime.app_data_root() == local_app_data / "EWasteManagement"
    assert runtime.database_path() == local_app_data / "EWasteManagement" / "data" / "scan_history.db"
    assert runtime.log_directory() == local_app_data / "EWasteManagement" / "logs"
    assert runtime.config_path() == local_app_data / "EWasteManagement" / "config" / ".env"
    assert runtime.frontend_dist_path() == bundle / "frontend"
    assert runtime.lifespan_model_path() == bundle / "models" / "lifespan"
    assert runtime.classifier_model_path("siglip2-base") == bundle / "models" / "classifier" / "siglip2-base"


def test_explicit_runtime_paths_are_expanded(monkeypatch, tmp_path):
    from app import runtime

    monkeypatch.setenv("EWASTE_DB_PATH", str(tmp_path / "custom" / "history.db"))
    monkeypatch.setenv("EWASTE_LOG_DIR", str(tmp_path / "custom logs"))
    monkeypatch.setenv("EWASTE_FRONTEND_DIR", str(tmp_path / "site"))
    monkeypatch.setenv("EWASTE_LIFESPAN_MODEL_DIR", str(tmp_path / "lifespan"))
    monkeypatch.setenv("EWASTE_CLASSIFIER_MODEL_PATH", str(tmp_path / "classifier"))

    assert runtime.database_path() == tmp_path / "custom" / "history.db"
    assert runtime.log_directory() == tmp_path / "custom logs"
    assert runtime.frontend_dist_path() == tmp_path / "site"
    assert runtime.lifespan_model_path() == tmp_path / "lifespan"
    assert runtime.classifier_model_path("ignored") == tmp_path / "classifier"


def test_runtime_public_config_exposes_no_backend_secrets(monkeypatch):
    from app.runtime import public_runtime_config

    monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", "pk_test_valid_browser_value")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )
    monkeypatch.setenv("DELETE_API_KEY", "must-never-leak")
    monkeypatch.setenv("CLERK_AUDIENCE", "private-audience")

    config = public_runtime_config()

    assert config["configured"] is True
    assert config["clerkPublishableKey"] == "pk_test_valid_browser_value"
    serialized = json.dumps(config)
    assert "must-never-leak" not in serialized
    assert "private-audience" not in serialized
    assert "JWKS" not in serialized.upper()


def test_runtime_public_config_rejects_live_or_placeholder_keys(monkeypatch):
    from app.runtime import public_runtime_config

    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )
    for key in ("pk_live_not_for_localhost", "pk_test_example", ""):
        monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", key)
        config = public_runtime_config()
        assert config["configured"] is False
        assert config["clerkPublishableKey"] is None
        assert config["errors"]


def test_classifier_snapshot_manifest_detects_changes(tmp_path):
    from app.runtime import verify_file_manifest

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    model_file = model_dir / "config.json"
    model_file.write_text('{"model_type":"siglip"}', encoding="utf-8")
    digest = hashlib.sha256(model_file.read_bytes()).hexdigest()
    (model_dir / "model_manifest.json").write_text(
        json.dumps({"files": {"config.json": digest}}), encoding="utf-8"
    )

    ok, errors = verify_file_manifest(model_dir)
    assert ok is True
    assert errors == []

    model_file.write_text("changed", encoding="utf-8")
    ok, errors = verify_file_manifest(model_dir)
    assert ok is False
    assert errors == ["hash mismatch: config.json"]


def test_single_origin_app_serves_spa_and_keeps_api_404(tmp_path, monkeypatch):
    from app.main import create_app

    frontend = tmp_path / "frontend"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text(
        "<!doctype html><html><body><div id='root'></div></body></html>",
        encoding="utf-8",
    )
    (frontend / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    (assets / "app-123.js").write_text("console.log('ok')", encoding="utf-8")

    monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", "pk_test_runtime")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )
    app = create_app(
        frontend_dir=frontend,
        require_frontend=True,
        enable_model_warmup=False,
    )

    with TestClient(app) as client:
        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["status"] == "online"

        config = client.get("/api/runtime-config")
        assert config.status_code == 200
        assert config.headers["cache-control"] == "no-store"
        assert config.json()["configured"] is True

        assert client.get("/").status_code == 200
        assert client.get("/dashboard").status_code == 200
        asset = client.get("/assets/app-123.js")
        assert asset.status_code == 200
        assert "immutable" in asset.headers["cache-control"]
        assert client.get("/favicon.svg").status_code == 200
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api").status_code == 404
        assert client.get("/health").status_code == 404
        assert client.get("/api/does-not-exist").status_code == 404


def _frontend_fixture(tmp_path: Path) -> Path:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    return frontend


def _configure_test_auth(monkeypatch) -> None:
    monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", "pk_test_runtime")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )


def test_readiness_reports_success_with_sanitized_components(tmp_path, monkeypatch):
    from app.main import create_app

    _configure_test_auth(monkeypatch)
    app = create_app(
        frontend_dir=_frontend_fixture(tmp_path),
        require_frontend=True,
        enable_model_warmup=False,
    )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert all(component["ready"] for component in payload["components"].values())
    assert str(tmp_path) not in response.text


def test_readiness_and_http_config_reject_missing_or_live_auth(tmp_path, monkeypatch):
    from app.main import create_app

    frontend = _frontend_fixture(tmp_path)
    monkeypatch.setenv("DELETE_API_KEY", "must-never-leak")
    monkeypatch.setenv(
        "CLERK_JWKS_URL",
        "https://valid-instance.clerk.accounts.dev/.well-known/jwks.json",
    )

    for key in ("", "pk_live_not-for-localhost"):
        if key:
            monkeypatch.setenv("EWASTE_CLERK_PUBLISHABLE_KEY", key)
        else:
            monkeypatch.delenv("EWASTE_CLERK_PUBLISHABLE_KEY", raising=False)
            monkeypatch.delenv("VITE_CLERK_PUBLISHABLE_KEY", raising=False)
        app = create_app(
            frontend_dir=frontend,
            require_frontend=True,
            enable_model_warmup=False,
        )
        with TestClient(app) as client:
            config = client.get("/api/runtime-config")
            readiness = client.get("/health/ready")

        assert config.status_code == 200
        assert config.json()["configured"] is False
        assert config.json()["clerkPublishableKey"] is None
        assert readiness.status_code == 503
        assert readiness.json()["components"]["authentication"]["ready"] is False
        assert "must-never-leak" not in config.text
        assert "must-never-leak" not in readiness.text


def test_readiness_detects_database_frontend_and_lifespan_failures(tmp_path, monkeypatch):
    from app import main as main_module

    _configure_test_auth(monkeypatch)
    missing_frontend = tmp_path / "missing-frontend"
    corrupt_lifespan = tmp_path / "lifespan"
    corrupt_lifespan.mkdir()
    (corrupt_lifespan / "model_manifest.json").write_text(
        json.dumps({"files": {"pipeline.pkl": "0" * 64}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("EWASTE_SKIP_MODEL_PRELOAD", "0")
    monkeypatch.setattr(main_module, "database_healthcheck", lambda: (False, "database unavailable"))
    monkeypatch.setattr(main_module, "lifespan_model_path", lambda: corrupt_lifespan)

    app = main_module.create_app(
        frontend_dir=missing_frontend,
        require_frontend=True,
        enable_model_warmup=False,
    )
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    components = response.json()["components"]
    assert components["database"] == {"ready": False, "error": "database unavailable"}
    assert components["frontend"] == {"ready": False, "required": True}
    assert components["lifespan_models"]["ready"] is False
    assert components["lifespan_models"]["errors"] == ["missing file: pipeline.pkl"]


def test_packaged_classifier_fails_fast_when_snapshot_missing(monkeypatch, tmp_path):
    from app import model

    monkeypatch.setattr(model, "LOCAL_MODEL_PATH", tmp_path / "missing-model")

    try:
        model._build_model_pipeline()
    except RuntimeError as exc:
        assert str(exc) == "Bundled classifier model directory is missing"
    else:
        raise AssertionError("missing packaged model should fail")


def test_packaged_classifier_rejects_corrupt_snapshot(monkeypatch, tmp_path):
    from app import model

    snapshot = tmp_path / "classifier"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("changed", encoding="utf-8")
    (snapshot / "model_manifest.json").write_text(
        json.dumps({"files": {"config.json": "0" * 64}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(model, "LOCAL_MODEL_PATH", snapshot)

    try:
        model._build_model_pipeline()
    except RuntimeError as exc:
        assert str(exc) == "Bundled classifier model failed integrity verification"
    else:
        raise AssertionError("corrupt packaged model should fail")


def test_packaged_classifier_passes_offline_flag_without_duplicate_model_kwargs(
    monkeypatch, tmp_path
):
    import sys
    from types import SimpleNamespace

    from app import model

    snapshot = tmp_path / "classifier"
    snapshot.mkdir()
    config = snapshot / "config.json"
    config.write_text("{}", encoding="utf-8")
    (snapshot / "model_manifest.json").write_text(
        json.dumps({"files": {"config.json": hashlib.sha256(b"{}").hexdigest()}}),
        encoding="utf-8",
    )
    calls = []

    def fake_pipeline(*args, **kwargs):
        calls.append((args, kwargs))
        return "offline-pipeline"

    monkeypatch.setattr(model, "LOCAL_MODEL_PATH", snapshot)
    monkeypatch.setattr(model, "MODEL_SOURCE", str(snapshot))
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(pipeline=fake_pipeline),
    )

    assert model._build_model_pipeline() == "offline-pipeline"
    assert calls[0][1]["local_files_only"] is True
    assert "model_kwargs" not in calls[0][1]
    assert calls[0][1]["device"] == -1
