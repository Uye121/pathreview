## Solution plan

**Issue:** [Add rate limiting per IP address in addition to per user](https://github.com/ascherj/pathreview/issues/70)

### Understand
The `RateLimiter` class in [safety/rate_limiter.py](./safety/rate_limiter.py) exists but is never wired into the request path, so any client, authenticated or not, can make unlimited requests. The fix is a middleware that enforces the rolling-window limiter on every request, per IP for everyone and per user on top for authenticated traffic.

### Map
Which files, functions, or modules are involved?
- [safety/rate_limiter.py](./safety/rate_limiter.py) — reuse the existing rolling-window limiter (fails open on Redis errors).
- api/middleware/rate_limit.py — new `RateLimitMiddleware` for per-IP + per-user enforcement.
- [api/main.py](./api/main.py) — register the middleware with an injected Redis client and limit.
- [core/config.py](./core/config.py) — source of `rate_limit_per_minute` and `redis_url`.
- [core/security.py](./core/security.py) — `decode_access_token`, to identify the user for the per-user budget.
- tests/ — add tests for the middleware.

### Plan
What are the steps to fix this issue?

1. **Create the middleware** (`api/middleware/rate_limit.py`): a `RateLimitMiddleware` that takes its dependencies via the constructor (`redis_client`, `limit`, `window_seconds`, `trust_proxy`, `exempt_paths`) rather than building Redis internally, so it stays testable. It builds one `RateLimiter` from the injected client and, per request, resolves the client IP and calls `check_rate_limit`.
2. **Enforce on reject**: when a budget is exceeded, short-circuit with a `429` JSON (`{"detail": "Rate limit exceeded"}`) carrying `Retry-After` (the window length) and `X-RateLimit-*` headers. Successful responses also carry `X-RateLimit-Limit` / `X-RateLimit-Remaining` (the tighter of the IP/user remaining).
3. **Wire it in** ([api/main.py](./api/main.py)): register the middleware globally so it runs before routing and covers public and authenticated endpoints alike. Register it inside `RequestIDMiddleware` so rejection logs still carry the `request_id`. Pass `redis_client=redis.Redis.from_url(settings.redis_url)` and `limit=settings.rate_limit_per_minute`.
4. **Namespace the identifiers** so per-IP counters don't collide with per-user counters: `ip:<addr>` and `user:<id>`. Authenticated requests must pass both checks.
5. **Resolve the client IP safely** (spoofing defense): trust `X-Forwarded-For` only when `trust_proxy=True` (off by default), and only when the value parses as a valid IP (`ipaddress.ip_address()`); otherwise use the socket peer (`request.client.host`), falling back to an `"unknown"` sentinel.
6. **Exempt monitoring paths**: let `/health` bypass limiting so monitoring isn't throttled, configurable via `exempt_paths`.
7. **Add tests** verifying: under-limit requests pass with headers; the `(limit+1)`th request gets `429`; distinct IPs and distinct users are counted independently; the per-user budget binds even across fresh IPs; spoofed/invalid `X-Forwarded-For` cannot dodge the limit when the proxy is untrusted; `/health` is exempt; and the app fails open when Redis is unreachable.

### Inputs & outputs
- **Input:** an incoming HTTP request; the resolved client IP (socket peer, or a validated `X-Forwarded-For` first hop when `trust_proxy` is enabled), the optional Bearer-token user id, and `settings.rate_limit_per_minute`.
- **Output / changes:** requests within budget are served normally with `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers; requests over either the per-IP or per-user budget within the 60s window receive `429` with `Retry-After` and `X-RateLimit-Remaining: 0`.

### Risks & unknowns
- **Proxy / IP spoofing:** `X-Forwarded-For` is client-controllable; trusting it blindly lets an attacker rotate the header to dodge the limit. The plan only trusts it when `trust_proxy=True` and the value is a valid IP; otherwise it uses the socket IP. `trust_proxy` stays off until the deployment topology (whether a known proxy fronts the API) is confirmed.
- **Shared IPs (NAT / corporate / mobile):** many legitimate users behind one IP could be throttled together. 60/min is likely fine but should be reviewed; the per-user budget softens this for authenticated traffic.

### Edge cases
- Missing/empty `request.client` (e.g. certain test clients) → fall back to the `"unknown"` sentinel identifier.
- `X-Forwarded-For` with multiple hops → use the first (original client) entry, trimmed, only when `trust_proxy` is enabled.
- Malformed `X-Forwarded-For` → log and ignore, fall back to the socket peer.
- Redis down or throwing → fail open (allow the request), log the error.
- Health-check endpoint → exempt via `exempt_paths` (`/health`).
- `rate_limit_per_minute` set to 0 or negative → the limiter treats a non-positive limit as "block all"; config validation belongs in `core/config.py`.
