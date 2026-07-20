"""Regression tests for deterministic offline classifier snapshot preparation."""

import hashlib
import json

from app.runtime import verify_file_manifest
from scripts.prepare_classifier_model import MODEL_REVISION, build_manifest


def test_classifier_preparer_hashes_all_flat_snapshot_files(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"weights")

    manifest = build_manifest(tmp_path)
    (tmp_path / "model_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    assert manifest == {
        "files": {
            "config.json": hashlib.sha256(b"{}").hexdigest(),
            "model.safetensors": hashlib.sha256(b"weights").hexdigest(),
        }
    }
    assert verify_file_manifest(tmp_path) == (True, [])
    assert len(MODEL_REVISION) == 40
