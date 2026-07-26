## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/70

**Issue title:** Add rate limiting per IP address in addition to per user

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
Pathview currently rate limits requests for authenticated users, but not for unauthenticated users. This allows for unauthenticated users to abuse the lack of rate limit and burn through system resources. The fix is to add a secondary layer that limits number of requests regardless of authentication.

**Branch name:** feat/70-rate-limiting-per-ip

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

---
## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/Uye121/pathreview/commit/6d6eb75dd263e222d999ff5c1778eacd12dcf091

**Reproduction summary:** I used Claude to create a script to send 70 requests to `/auth/login` with random credentials. It should return mostly 401s with a couple 429s for too many requests, but it only returns 401s.

**PLAN.md link:** [link to PLAN.md in your fork]

**Walkthrough video (recommended):** N/A

**Blockers or open questions:** N/A