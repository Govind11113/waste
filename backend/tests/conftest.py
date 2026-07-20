"""Shared backend test isolation.

Environment switches are installed before any application module import. This
prevents collection-time database initialization from touching the production
SQLite file and prevents native ML pickle preload during unit/API tests.
"""

import os
import tempfile
from pathlib import Path

import pytest

_TEST_DB_DIRECTORY = tempfile.TemporaryDirectory(prefix="ewaste_pytest_")
_TEST_SESSION_DB = Path(_TEST_DB_DIRECTORY.name) / "scan_history.db"

# Set these unconditionally for the pytest process. Individual tests can still
# monkeypatch app.db.DB_PATH to obtain a fresh per-test database.
os.environ["EWASTE_DB_PATH"] = str(_TEST_SESSION_DB)
os.environ["EWASTE_SKIP_MODEL_PRELOAD"] = "1"

from app import db as db_module  # noqa: E402  (environment must be set first)


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Run production DB functions against a fresh database for one test."""
    temp_path = tmp_path / "history.db"
    monkeypatch.setattr(db_module, "DB_PATH", temp_path)
    db_module.init_db()
    yield db_module


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Remove the collection-time database and its temporary directory."""
    _TEST_DB_DIRECTORY.cleanup()


__all__ = ["temp_db", "db_module"]
