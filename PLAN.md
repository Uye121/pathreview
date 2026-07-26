## Solution plan

**Issue:** [Add rate limiting per IP address in addition to per user](https://github.com/ascherj/pathreview/issues/70)

### Understand
The RateLimiter class in [safety/rate_limiter.py](./safety/rate_limiter.py) is not configured to rate limit the requests, which leads to any users (authenticated or not) to be able to make unlimited number of requests. The expected behavior should be to limit the number of requests made by any users.

### Map
Which files, functions, or modules are involved?
- [safety/rate_limiter.py](./safety/rate_limiter.py) — reuse existing rate limiter.
- api/middleware/rate_limit.py — create middleware to get client IP to help with the rate limiting.
- api/main.py — add the middleware to the app.
- core/config.py — reuse rate_limit_per_minute for IP limiting.
- tests/ — add a test to verify request limitation by IP.

### Plan
What are the steps to fix this issue?

1. **Create the middleware** (`api/middleware/rate_limit.py`): a `RateLimitMiddleware` that constructs one `RateLimiter` from `redis.Redis.from_url(settings.redis_url)`, resolves the client IP (`X-Forwarded-For` first hop, else `request.client.host`), and calls `check_rate_limit(ip, limit=settings.rate_limit_per_minute, window_seconds=60)`.
2. **Enforce on reject**: when not allowed, short-circuit with a `429 Too Many Requests` JSON
3. **Wire it in** ([api/main.py](./api/main.py)): register the middleware globally so it runs before routing and covers public and authenticated endpoints alike. Keep per-IP limiting as a secondary layer alongside any per-user limiting, not a replacement.
4. **Namespace the identifier** so per-IP counters don't collide with per-user counters (e.g. `ip:<addr>` vs `user:<id>`).
5. **Add tests** verifying: under-limit requests pass, the `(limit+1)`th from one IP gets `429`, distinct IPs are counted independently, and the app fails open if Redis is unreachable.

### Inputs & outputs
- **Input:** an incoming HTTP request; the client IP (from `X-Forwarded-For` or the socket) and `settings.rate_limit_per_minute`.
- **Output / changes:** requests within the limit are served normally with rate-limit headers; requests over the limit for a given IP within the 60s window receive `429` with `Retry-After`.

### Risks & unknowns
- **Proxy / IP spoofing:** `X-Forwarded-For` is client-controllable; trusting it blindly lets an attacker rotate the header to dodge the limit. Only trust it behind a known proxy; otherwise use the socket IP. Deployment topology needs confirming.
- **Shared IPs (NAT / corporate / mobile):** many legitimate users behind one IP could be throttled together. 60/min is likely fine but should be reviewed.
- **Redis availability:** the limiter already **fails open** on Redis errors([rate_limiter.py:60-63](./safety/rate_limiter.py#L60)), so an outage won't hard-fail requests but will silently disable limiting. The sync Redis client inside async middleware also blocks the event loop under load — acceptable now, revisit with `redis.asyncio` if it matters.

### Edge cases
- Missing/empty `request.client` (e.g. certain test clients) → fall back to a sentinel identifier.
- `X-Forwarded-For` with multiple hops → use the first (original client) entry, trimmed.
- Redis down or throwing → fail open (allow the request), log the error.
- `rate_limit_per_minute` set to 0 or negative → validate config / treat as "block all".
- Health-check and docs endpoints → decide whether to exempt (e.g. skip `/health`) so monitoring isn't throttled.
