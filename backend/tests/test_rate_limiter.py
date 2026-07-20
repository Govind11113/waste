"""Unit tests for the in-process per-user scan rate limiter (no network)."""

from app.routers.classifier import RateLimiter


def test_allows_up_to_limit_then_blocks():
    rl = RateLimiter(limit=3, window=60)
    assert rl.check("user_a") is True   # 1
    assert rl.check("user_a") is True   # 2
    assert rl.check("user_a") is True   # 3
    assert rl.check("user_a") is False  # 4 -> over limit


def test_remaining_counts_down():
    rl = RateLimiter(limit=5, window=60)
    assert rl.remaining("u") == 5
    rl.check("u")
    rl.check("u")
    assert rl.remaining("u") == 3


def test_remaining_never_negative():
    rl = RateLimiter(limit=2, window=60)
    for _ in range(10):
        rl.check("u")
    assert rl.remaining("u") == 0


def test_users_are_isolated():
    rl = RateLimiter(limit=1, window=60)
    assert rl.check("alice") is True
    assert rl.check("alice") is False
    # Bob's bucket is independent of Alice's.
    assert rl.check("bob") is True
    assert rl.remaining("bob") == 0
    assert rl.remaining("alice") == 0


def test_concurrent_requests_never_exceed_limit():
    from concurrent.futures import ThreadPoolExecutor

    rl = RateLimiter(limit=5, window=60)
    with ThreadPoolExecutor(max_workers=20) as pool:
        allowed = list(pool.map(lambda _: rl.check("shared-user"), range(100)))

    assert sum(allowed) == 5
    assert rl.remaining("shared-user") == 0
