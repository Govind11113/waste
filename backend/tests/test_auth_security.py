"""Security-focused Clerk JWKS tests with no network or real key generation."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app import auth


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def isolated_jwks(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(auth, "CLERK_JWKS_URL", "https://clerk.test/jwks.json")
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(
        auth.jwt.algorithms.RSAAlgorithm,
        "from_jwk",
        lambda key_data: f"public:{key_data['kid']}",
    )
    monkeypatch.setattr(
        auth,
        "_jwks_cache",
        {
            "keys": None,
            "expires_at": 0.0,
            "last_refresh_at": None,
            "retry_after": 0.0,
        },
    )
    monkeypatch.setattr(auth, "_unknown_kid_cache", OrderedDict())
    return clock


def _install_jwks_responses(monkeypatch, payloads, delay=0.0):
    calls = []
    calls_lock = threading.Lock()

    def fake_get(url, timeout):
        if delay:
            time.sleep(delay)
        with calls_lock:
            index = len(calls)
            calls.append((url, timeout))
        payload = payloads[min(index, len(payloads) - 1)]
        return _FakeResponse(payload)

    monkeypatch.setattr(auth.requests, "get", fake_get)
    return calls


def _jwks(*kids):
    return {"keys": [{"kid": kid, "kty": "RSA"} for kid in kids]}


def test_random_unknown_kids_cannot_force_repeated_refreshes(
    monkeypatch,
    isolated_jwks,
):
    calls = _install_jwks_responses(monkeypatch, [_jwks("known")])

    assert auth._fetch_jwks()["known"] == "public:known"
    for index in range(auth._UNKNOWN_KID_CACHE_MAX_SIZE + 50):
        assert auth._refresh_for_unknown_kid(f"attacker-{index}") is None

    # The initial fetch is fresh, so arbitrary ids do not clear it or fetch
    # again, and the fixed-size negative cache remains bounded.
    assert len(calls) == 1
    assert len(auth._unknown_kid_cache) == auth._UNKNOWN_KID_CACHE_MAX_SIZE

    isolated_jwks["now"] += auth._UNKNOWN_KID_REFRESH_INTERVAL_SECONDS + 1
    assert auth._refresh_for_unknown_kid("attacker-after-cooldown") is None
    assert len(calls) == 2

    for index in range(20):
        assert auth._refresh_for_unknown_kid(f"another-{index}") is None
    assert len(calls) == 2


def test_unknown_kid_refresh_is_single_flight_across_threads(
    monkeypatch,
    isolated_jwks,
):
    calls = _install_jwks_responses(
        monkeypatch,
        [_jwks("known"), _jwks("known")],
        delay=0.02,
    )
    auth._fetch_jwks()
    isolated_jwks["now"] += auth._UNKNOWN_KID_REFRESH_INTERVAL_SECONDS + 1

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(
            pool.map(
                auth._refresh_for_unknown_kid,
                [f"unknown-{index}" for index in range(24)],
            )
        )

    assert results == [None] * 24
    assert len(calls) == 2  # initial fetch + one coordinated early refresh


def test_legitimate_rotated_key_is_loaded_after_short_cooldown(
    monkeypatch,
    isolated_jwks,
):
    calls = _install_jwks_responses(
        monkeypatch,
        [_jwks("old-key"), _jwks("old-key", "rotated-key")],
    )
    auth._fetch_jwks()

    # A just-fetched set is authoritative during the short anti-abuse window.
    assert auth._refresh_for_unknown_kid("rotated-key") is None
    assert len(calls) == 1

    isolated_jwks["now"] += auth._UNKNOWN_KID_REFRESH_INTERVAL_SECONDS + 1
    assert auth._refresh_for_unknown_kid("rotated-key") == "public:rotated-key"
    assert len(calls) == 2


def test_oversized_kid_is_rejected_without_fetch(monkeypatch, isolated_jwks):
    calls = _install_jwks_responses(monkeypatch, [_jwks("known")])
    monkeypatch.setattr(
        auth.jwt,
        "get_unverified_header",
        lambda token: {"kid": "x" * (auth._MAX_KID_LENGTH + 1)},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert calls == []
