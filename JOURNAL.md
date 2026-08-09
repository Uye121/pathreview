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

## Week 10 — Iteration & reflection

### Reviewer feedback

**Feedback received:** [x] Yes  [ ] No — still awaiting review

**Summary of feedback:**
The reviewer provided positive feedback, noting that the middleware properly extends the existing RateLimiter without modifying its core behavior, and that using constructor injection for dependencies keeps the code clean and testable. They confirmed that the key requirements is enforced per-IP separation and per-user limitation, namespacing Redis keys to avoid collisions, handling authentication edge cases gracefully, and including solid test coverage for proxies, separate budgets, fail-open behavior, and exempt routes. They offered two minor suggestions for improvement: adding a brief comment in `api/main.py` to document the middleware registration order relative to RequestIDMiddleware and Redis client implementation as a shared application dependency or initialize at startup lifecycle if Redis usage grows in the future. Overall, they felt the implementation was well-scoped, aligned with the requirements, and the tests provided good confidence in both expected behavior and edge cases.

**How you responded:**
I addressed the reviewer's feedback by adding a comment in api/main.py that explains the middleware ordering rationale—specifically, why RequestIDMiddleware is registered after RateLimitMiddleware to ensure that rate-limit responses (429s) still include a request ID in the logs. For the Redis client, I kept the module-wide initialization for simplicity and accessibility across the application, but I also store it in `app.state.redis` during the lifespan startup so it can be consistently accessed through the application state when needed, giving us flexibility in how different parts of the codebase retrieve the client.
---

### Reflection

**What was harder than you expected?**
Balancing the implementation approach without over-engineering the solution or introducing unintended side effects was harder than I expected. There were several viable paths to implement the secondary rate-limiting layer, each with different trade-offs. I had to spend time understanding the different components (middleware ordering, Redis key structures, request context extraction) to determine the simplest approach that still met all the requirements. Working with the LLM helped me explore these options efficiently, but it took some back-and-forth to converge on a clean solution that would not introduce unnecessary abstractions.

**What did you learn about working in a large codebase?**
I learned that you don't need to understand every detail of the codebase to be effective. Gaining a high-level understanding of the application's architecture and core flows is usually sufficient. After that, I could focus on the specific files and modules that the feature touches. This targeted approach helped me move faster and avoid getting overwhelmed by the size of the codebase, while still ensuring I understood the relevant context to make safe changes.

**How did AI tools help — and where did they fall short?**
AI tools helped me quickly generate multiple design options and compare their trade-offs, which made the decision-making process much more efficient. The main limitation was that the generated code often focused only on the core happy path and omitted important edge cases—things like handling malformed headers or Redis timeouts. I had to actively review and extend the AI's output to make it production-ready.

**What would you do differently if you started over?**
I'd start by studying the architecture of network middlewares more thoroughly. For example, how they chain together, request headers, and constraints. A stronger foundation there would have made the rest of the work flow more smoothly.

**What are you most proud of from this module?**
I am proud of contributing to a open source project, even if it's a sandbox project. The experience showed me how much thoughtful design and documentation goes into open-source work. Contributing to it helped me learn and work with things that are on my to-learn bucket list.