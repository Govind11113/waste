"""Tests for release-stage safety, manifests, ZIP64 packaging, and hashes."""

import hashlib
import zipfile

import pytest

from scripts.package_windows_release import package_release


def test_package_release_hashes_and_archives_one_folder(tmp_path):
    stage = tmp_path / "EWasteManagement-Windows-x64-v3.0.0"
    (stage / "frontend").mkdir(parents=True)
    (stage / "EWasteManagement.exe").write_bytes(b"portable executable placeholder")
    (stage / "frontend" / "index.html").write_text("<div>app</div>", encoding="utf-8")
    output = tmp_path / "release" / "EWasteManagement.zip"

    result = package_release(stage, output)

    assert result == output
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    assert output.with_suffix(".zip.sha256").read_text(encoding="ascii").startswith(expected_hash)
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        prefix = f"{stage.name}/"
        assert prefix + "EWasteManagement.exe" in names
        assert prefix + "frontend/index.html" in names
        assert prefix + "RELEASE_MANIFEST.sha256" in names
        assert archive.testzip() is None


def test_package_release_refuses_mutable_or_secret_files(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "EWasteManagement.exe").write_bytes(b"exe")
    (stage / ".env").write_text("SECRET=value", encoding="utf-8")

    with pytest.raises(ValueError, match="environment file"):
        package_release(stage, tmp_path / "unsafe.zip")
