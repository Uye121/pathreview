## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/70

**Issue title:** Add rate limiting per IP address in addition to per user

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
Pathview currently rate limits requests for authenticated users, but not for unauthenticated users. This allows for unauthenticated users to abuse the lack of rate limit and burn through system resources. The fix is to add a secondary layer that limits number of requests regardless of authentication.

**Branch name:** feat/70-rate-limiting-per-ip

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger