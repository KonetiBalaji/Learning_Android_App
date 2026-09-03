# Authentication admission limits

Status: implemented and tested locally; production hardening remains partial.

Registration, password login and Google token exchange share one admission window
per ASGI client peer. The default is 30 attempts in 60 seconds, configurable with
`LEARNING_AUTH_ATTEMPTS` (1–1000) and `LEARNING_AUTH_WINDOW_SECONDS` (1–3600).
These are initial engineering defaults, not a user-approved production capacity
policy. Invalid values fail settings validation; zero does not disable protection.
All admitted attempts count, including successful authentication. Active sessions
and learning endpoints are not blocked by this authentication-only counter.

Excess attempts receive generic HTTP 429 and integer `Retry-After` seconds.
The window starts at the first admitted attempt; rejected attempts do not extend
it. This fixed-window design can admit two bursts near a window boundary and is
not a strict rolling-rate guarantee. Android already renders a safe 429 wait
message; it does not yet display a countdown or automatically retry sign-in.

SQLite serializes admission with `BEGIN IMMEDIATE`. Workers sharing the same
database share limits, and a restart does not clear them. The additive
`auth_attempt_windows` table contains only a domain-separated HMAC-SHA256 peer
digest, expiry and attempt count. The HMAC uses the configured JWT secret; no raw
IP, email, password or Google token is stored by this feature. A strong production
secret is essential; changing it resets peer identity for these counters.
Expired rows are reclaimed on the next admission attempt; the table is capped at
10,000 active peer windows. Capacity exhaustion or database errors fail closed
with generic 503 and a five-second retry hint. SQLite storage is not encrypted;
backups include the digests, so they must still be treated as pseudonymous data.

The application ignores arbitrary `Forwarded` and `X-Forwarded-For` headers.
The serving stack can rewrite the ASGI peer before the application sees it:
production must explicitly configure and verify trusted proxy addresses, prohibit
direct bypass of the edge, and never blindly trust forwarding from any client.
Without correct proxy configuration all users may share the proxy's limit.
Shared school/home networks also share a peer limit; staging capacity tests must
evaluate that usability tradeoff before release.

## Verification and remaining work

Focused tests cover expiry and exact retry timing, independent peers, persisted
state through new connections/settings, digest-only records, 20 concurrent
attempts admitting exactly three, capacity rejection/reclamation, generic database
failure, invalid configuration and all three HTTP authentication routes sharing
limits. The route test includes successful logins, spoofed forwarding headers,
continued authenticated profile access and recovery after expiry.

On 2026-09-03 the 11 focused tests passed, followed by the full backend suite:
**277 passed, 1 existing Windows symlink-privilege skip**, with the existing
Starlette/httpx warning. No live provider calls, production rollout or Android
throttle device test was performed in this slice.

This is not account-based lockout, credential-stuffing prevention, a provider-cost
quota, a request-body size limit, a distributed multi-database limit or a DDoS
shield. JSON parsing can occur before route dependencies, so request size, load
and connection limits still belong at the serving boundary. Distributed attacks,
IPv6 peer rotation, host clock changes, database contention, authentication audit
events, privacy retention and operational alerts remain release work. A parent/
learner-safe account-based policy also needs deliberate recovery and denial-of-
service handling rather than silently locking student accounts indefinitely.

Reference: [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
describes throttling and warns that account-lockout design must balance attack
resistance against denial of service. This peer admission layer does not claim
to satisfy its broader recommendations by itself.
