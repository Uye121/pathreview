## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/70

**Issue title:** Add rate limiting per IP address in addition to per user

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
Pathview currently rate limits requests for authenticated users, but not for unauthenticated users. This allows for unauthenticated users to abuse the lack of rate limit and burn through system resources. The fix is to add a secondary layer that limits number of requests regardless of authentication.

**Branch name:** feat/70-rate-limiting-per-ip

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/Uye121/pathreview/commit/6d6eb75dd263e222d999ff5c1778eacd12dcf091

**Reproduction summary:** I used Claude to create a script to send 70 requests to `/auth/login` with random credentials. It should return mostly 401s with a couple 429s for too many requests, but it only returns 401s.

**PLAN.md link:** [link to PLAN.md in your fork]

**Walkthrough video (recommended):** N/A

**Blockers or open questions:** N/A

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:** Tasks 1 - 7 from PLAN.md are implemented. [RateLimitMiddleware](api/middleware/rate_limit.py) is registered globally in `api/main.py` to resolve the client IP if `trust_proxy=True` and IP is valid, else it uses the socket peer. Requests exceed the limit will receive a `429` with `Retry-After` and `X-RateLimit-*` headers. `/health` is exempt from the rate limiter. Nine new unit tests were created to test the middleware. No new errors were introduced as a result of the changes. 

**Next steps:** Create end-to-end/load test to verify that the fix actually works on the production application.

**Blockers:** None.

---

### Check-in 2 (end of week)

**PR link:** https://github.com/Uye121/pathreview/pull/1

**Branch:** `feat/70-rate-limiting-per-ip`

**What you built:**
A secondary RateLimitMiddleware that uses client IP address to rate limit requests regardless of user authentication. It returns 429 to users making too many requests at a given time. It uses a module-level Redis client that fails open on errors, ensuring the API remains available even when Redis is down.

**Tests added or updated:**
Created [tests/unit/test_rate_limit_middleware.py](./tests/unit/test_rate_limit_middleware.py) with 9 tests. These tests validate the rate limiting middleware's core behavior. They verify that requests below the limit succeed while the (limit+1)th request receives a 429 response, and that rate limits are enforced independently per IP address and per authenticated user. The tests also confirm that X-Forwarded-For headers are only respected when trust_proxy is enabled, preventing IP spoofing. Additionally, they ensure that exempt paths like /health bypass rate limiting entirely. Finally, the tests exercise the fail-open mechanism using a BrokenRedis mock, confirming that when Redis is unreachable, the API continues to accept all requests rather than blocking traffic.


**Self-review confirmation:** [x] make check passes  [x] make test-unit passes

**Draft PR feedback received from:** 
[kaiser1x](https://github.com/Uye121/pathreview/pull/1#issuecomment-5137231482)
The PR feedbacks were addressed in commit `62439960ad02a0bcaaee7706767e9d70db10c899` by creating a module-level Redis client that is accessible anywhere in the application and a comment on the significance of ordering the middleware with `RequestIDMiddleware` being first to bind the requests with ID before `RateLimitMiddleware` can make use of the ID in logging.
