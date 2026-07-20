"""Clerk JWT authentication for protected endpoints.

Session tokens issued by Clerk (https://clerk.com) are RS256-signed JWTs whose
signing keys are published as a JSON Web Key Set (JWKS). The frontend obtains a
token via ``useAuth().getToken()`` and sends it as ``Authorization: Bearer
<jwt>``; ``get_current_user`` validates it against the JWKS and returns the
Clerk subject (``sub``), the user id.

Required env:
    CLERK_JWKS_URL — e.g. https://<clerk-frontend-api>/.well-known/jwks.json
Optional env:
    CLERK_ISSUER — verify the ``iss`` claim (the Clerk Frontend API origin)
    CLERK_AUDIENCE — verify the ``aud`` claim, if you pinned an audience
"""

from collections import OrderedDict
import hashlib
import os
import threading
import time
from typing import Optional

import jwt
import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_ISSUER: Optional[str] = os.getenv("CLERK_ISSUER")
CLERK_AUDIENCE: Optional[str] = os.getenv("CLERK_AUDIENCE")

# ``HTTPBearer`` reads the ``Authorization: Bearer <token>`` header.
# ``auto_error=False`` lets us return our own 401 instead of FastAPI's default.
_security = HTTPBearer(auto_error=False)

# JWKS state is protected by one lock. Network refreshes happen while holding
# the lock so concurrent cold starts and key rotations are single-flight.
_jwks_lock = threading.Lock()
_jwks_cache: dict = {
    "keys": None,
    "expires_at": 0.0,
    "last_refresh_at": None,
    "retry_after": 0.0,
}
_JWKS_TTL_SECONDS = 60 * 60  # 1 hour
_JWKS_FETCH_RETRY_SECONDS = 10

# An unknown ``kid`` may indicate a legitimate Clerk key rotation, but it is
# also attacker-controlled input. At most one early refresh is allowed per
# interval, and fixed-size hashes of recently rejected ids are retained so a
# repeated id cannot trigger work. Successful refreshes clear this cache so a
# newly published key is accepted immediately.
_UNKNOWN_KID_REFRESH_INTERVAL_SECONDS = 60
_UNKNOWN_KID_TTL_SECONDS = 60
_UNKNOWN_KID_CACHE_MAX_SIZE = 256
_unknown_kid_cache: "OrderedDict[bytes, float]" = OrderedDict()
_MAX_KID_LENGTH = 256


class _AuthConfigError(RuntimeError):
    """Raised when the server is missing or has invalid auth configuration."""


def _negative_cache_key(kid: str) -> bytes:
    """Return a fixed-size key so attacker-controlled ids cannot bloat memory."""
    return hashlib.sha256(kid.encode("utf-8", errors="surrogatepass")).digest()


def _prune_unknown_kids_locked(now: float) -> None:
    expired = [key for key, expires_at in _unknown_kid_cache.items() if expires_at <= now]
    for key in expired:
        _unknown_kid_cache.pop(key, None)


def _remember_unknown_kid_locked(kid: str, now: float) -> None:
    cache_key = _negative_cache_key(kid)
    _unknown_kid_cache[cache_key] = now + _UNKNOWN_KID_TTL_SECONDS
    _unknown_kid_cache.move_to_end(cache_key)
    while len(_unknown_kid_cache) > _UNKNOWN_KID_CACHE_MAX_SIZE:
        _unknown_kid_cache.popitem(last=False)


def _download_jwks_locked() -> dict:
    """Fetch and parse Clerk keys. Caller must hold ``_jwks_lock``."""
    response = requests.get(CLERK_JWKS_URL, timeout=10)
    response.raise_for_status()
    jwks = response.json()
    if not isinstance(jwks, dict):
        raise _AuthConfigError("JWKS response was not an object")

    keys = {}
    for key_data in jwks.get("keys", []):
        if not isinstance(key_data, dict):
            continue
        kid = key_data.get("kid")
        if not isinstance(kid, str) or not kid:
            continue
        try:
            keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
        except (jwt.PyJWTError, TypeError, ValueError):
            # Ignore an individual malformed key as long as the set contains at
            # least one usable signing key.
            continue

    if not keys:
        raise _AuthConfigError("JWKS contained no signing keys")

    now = time.monotonic()
    _jwks_cache["keys"] = keys
    _jwks_cache["expires_at"] = now + _JWKS_TTL_SECONDS
    _jwks_cache["last_refresh_at"] = now
    _jwks_cache["retry_after"] = 0.0
    _unknown_kid_cache.clear()
    return keys


def _fetch_jwks() -> dict:
    """Return ``{kid: public_key}``, using a single-flight TTL cache."""
    if not CLERK_JWKS_URL:
        raise _AuthConfigError("CLERK_JWKS_URL not configured on server")

    with _jwks_lock:
        now = time.monotonic()
        keys = _jwks_cache.get("keys")
        if keys is not None and now < _jwks_cache.get("expires_at", 0.0):
            return keys

        # Bound retry traffic during a Clerk/network outage even when no usable
        # cache exists. Callers still receive the same transient failure.
        if now < _jwks_cache.get("retry_after", 0.0):
            raise requests.RequestException("JWKS refresh is temporarily throttled")

        try:
            return _download_jwks_locked()
        except requests.RequestException:
            _jwks_cache["retry_after"] = now + _JWKS_FETCH_RETRY_SECONDS
            raise


def _refresh_for_unknown_kid(kid: str) -> object | None:
    """Refresh once when permitted and return the key for ``kid`` if present.

    The decision, refresh, and negative-cache update are one locked operation.
    This prevents concurrent or ever-changing unknown ids from causing a JWKS
    fetch stampede while permitting a real rotation after the short cooldown.
    """
    with _jwks_lock:
        now = time.monotonic()
        keys = _jwks_cache.get("keys") or {}

        # Another request may have completed a rotation refresh while this
        # request was waiting for the lock.
        public_key = keys.get(kid)
        if public_key is not None:
            return public_key

        _prune_unknown_kids_locked(now)
        negative_key = _negative_cache_key(kid)
        if negative_key in _unknown_kid_cache:
            _unknown_kid_cache.move_to_end(negative_key)
            return None

        last_refresh_at = _jwks_cache.get("last_refresh_at")
        if (
            last_refresh_at is not None
            and now - last_refresh_at < _UNKNOWN_KID_REFRESH_INTERVAL_SECONDS
        ):
            _remember_unknown_kid_locked(kid, now)
            return None

        # Reserve the refresh slot before network I/O. A failed refresh is also
        # throttled, otherwise an outage plus random kids could hammer Clerk.
        _jwks_cache["last_refresh_at"] = now
        if now < _jwks_cache.get("retry_after", 0.0):
            _remember_unknown_kid_locked(kid, now)
            return None

        try:
            keys = _download_jwks_locked()
        except requests.RequestException:
            _jwks_cache["retry_after"] = now + _JWKS_FETCH_RETRY_SECONDS
            _remember_unknown_kid_locked(kid, now)
            raise
        except _AuthConfigError:
            _remember_unknown_kid_locked(kid, now)
            raise

        public_key = keys.get(kid)
        if public_key is None:
            _remember_unknown_kid_locked(kid, time.monotonic())
        return public_key


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security),
) -> str:
    """Validate the Clerk Bearer JWT and return the user id (``sub`` claim).

    Applied as a router-level dependency so every endpoint under ``/api/v1``
    requires a valid Clerk session. Returns 401 on token failures, 503 when the
    JWKS endpoint is transiently unavailable, and 500 only for server config.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Malformed token")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing key id")
    if not isinstance(kid, str) or len(kid) > _MAX_KID_LENGTH:
        raise HTTPException(status_code=401, detail="Invalid key id")

    try:
        keys = _fetch_jwks()
    except _AuthConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except requests.RequestException:
        # Transient: Clerk or the network is unavailable; tell the client to retry.
        raise HTTPException(status_code=503, detail="Could not fetch signing keys")

    public_key = keys.get(kid)
    if public_key is None:
        try:
            public_key = _refresh_for_unknown_kid(kid)
        except (_AuthConfigError, requests.RequestException):
            # Preserve the existing unknown-key response rather than exposing
            # rotation endpoint details to unauthenticated callers.
            raise HTTPException(status_code=401, detail="Unknown signing key")
    if public_key is None:
        raise HTTPException(status_code=401, detail="Unknown signing key")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=CLERK_AUDIENCE,
            issuer=CLERK_ISSUER,
            # Skip aud/iss checks when not configured (None == not provided).
            options={
                "verify_aud": CLERK_AUDIENCE is not None,
                "verify_iss": CLERK_ISSUER is not None,
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")
    return user_id
