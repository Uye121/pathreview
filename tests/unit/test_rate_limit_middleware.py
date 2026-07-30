"""Tests for the RateLimitMiddleware (api/middleware/rate_limit.py)."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.middleware.rate_limit import RateLimitMiddleware
from core.security import create_access_token


class FakeRedis:
    """Minimal in-memory stand-in implementing the sorted-set ops the
    RateLimiter uses, so the real limiter logic runs under test."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, float]] = {}

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> None:
        members = self.store.get(key, {})
        for member in [m for m, s in members.items() if min_score <= s <= max_score]:
            del members[member]

    def zcard(self, key: str) -> int:
        return len(self.store.get(key, {}))

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        self.store.setdefault(key, {}).update(mapping)

    def expire(self, key: str, seconds: int) -> None:
        pass


class BrokenRedis:
    """Redis stand-in whose every operation raises, to exercise fail-open."""

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise Exception("redis is down")

        return _raise


def make_client(redis_client: Any, limit: int = 3, **kwargs: Any) -> TestClient:
    """Build a minimal app with only RateLimitMiddleware and dummy routes."""
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client, limit=limit, **kwargs)
    return TestClient(app)


def bearer(user_id: str) -> dict[str, str]:
    """Build an Authorization header carrying a valid token for user_id."""
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user_id})}"}


@pytest.mark.unit
class TestRateLimitMiddleware:
    def test_under_limit_requests_pass(self) -> None:
        """Requests below the limit all succeed and carry rate-limit headers."""
        client = make_client(FakeRedis(), limit=3)

        for _ in range(3):
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert resp.headers["X-RateLimit-Limit"] == "3"
            assert "X-RateLimit-Remaining" in resp.headers

    def test_limit_plus_one_rejected_with_429(self) -> None:
        """The (limit+1)th request from one IP is rejected with 429."""
        client = make_client(FakeRedis(), limit=3, window_seconds=60)

        for _ in range(3):
            assert client.get("/ping").status_code == 200

        resp = client.get("/ping")
        assert resp.status_code == 429
        assert resp.json() == {"detail": "Rate limit exceeded"}
        assert resp.headers["Retry-After"] == "60"
        assert resp.headers["X-RateLimit-Remaining"] == "0"

    def test_distinct_ips_counted_independently(self) -> None:
        """With a trusted proxy, one IP hitting its limit does not affect another."""
        client = make_client(FakeRedis(), limit=3, trust_proxy=True)

        for _ in range(3):
            assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
        assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429

        # A different IP is unaffected.
        assert client.get("/ping", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200

    def test_forwarded_for_ignored_when_proxy_untrusted(self) -> None:
        """With trust_proxy off, spoofed X-Forwarded-For cannot dodge the limit."""
        client = make_client(FakeRedis(), limit=3)  # trust_proxy defaults to False

        # Every request rotates the header, but all resolve to the same peer.
        for i in range(3):
            assert client.get("/ping", headers={"X-Forwarded-For": f"9.9.9.{i}"}).status_code == 200
        assert client.get("/ping", headers={"X-Forwarded-For": "9.9.9.99"}).status_code == 429

    def test_invalid_forwarded_for_falls_back_to_peer(self) -> None:
        """A malformed X-Forwarded-For is ignored, falling back to the peer IP."""
        client = make_client(FakeRedis(), limit=3, trust_proxy=True)

        for _ in range(3):
            assert client.get("/ping", headers={"X-Forwarded-For": "not-an-ip"}).status_code == 200
        # All counted under the peer, so the 4th is throttled.
        assert client.get("/ping", headers={"X-Forwarded-For": "not-an-ip"}).status_code == 429

    def test_per_user_budget_enforced_across_ips(self) -> None:
        """A user is throttled by their own budget even from fresh IPs."""
        client = make_client(FakeRedis(), limit=3, trust_proxy=True)
        headers = bearer("user-a")

        # Each request uses a distinct IP so only the user budget can bind.
        for i in range(3):
            resp = client.get("/ping", headers={**headers, "X-Forwarded-For": f"10.0.0.{i}"})
            assert resp.status_code == 200
        resp = client.get("/ping", headers={**headers, "X-Forwarded-For": "10.0.0.250"})
        assert resp.status_code == 429

    def test_distinct_users_counted_independently(self) -> None:
        """One user hitting their budget does not affect another user."""
        client = make_client(FakeRedis(), limit=3, trust_proxy=True)

        for i in range(3):
            resp = client.get(
                "/ping", headers={**bearer("user-a"), "X-Forwarded-For": f"11.0.0.{i}"}
            )
            assert resp.status_code == 200
        assert (
            client.get(
                "/ping", headers={**bearer("user-a"), "X-Forwarded-For": "11.0.0.250"}
            ).status_code
            == 429
        )

        # Different user, fresh IP -> allowed.
        assert (
            client.get(
                "/ping", headers={**bearer("user-b"), "X-Forwarded-For": "11.0.0.251"}
            ).status_code
            == 200
        )

    def test_health_path_exempt(self) -> None:
        """Exempt paths bypass rate limiting entirely."""
        client = make_client(FakeRedis(), limit=3)

        for _ in range(10):
            assert client.get("/health").status_code == 200

    def test_fails_open_when_redis_unreachable(self) -> None:
        """If Redis errors, requests are allowed through rather than blocked."""
        client = make_client(BrokenRedis(), limit=3)

        for _ in range(8):
            assert client.get("/ping").status_code == 200
