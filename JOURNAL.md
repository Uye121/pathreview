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

**PR link:** [link to your submitted pull request]

**Branch:** [the branch name you worked on, e.g. `fix/123-short-description`]

**What you built:**
[1–3 sentences summarizing what your fix does and how it works]

**Tests added or updated:**
[Which test files did you touch? What do they cover?]

**Self-review confirmation:** [ ] make check passes  [ ] make test-unit passes

**Draft PR feedback received from:** [name or Slack handle, or "none"]