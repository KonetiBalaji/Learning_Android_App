# Privacy-safe request observability

Every backend HTTP completion now emits one structured JSON log event through the
`uvicorn.error.learning.http` logger. The event contains only a UUID request ID, HTTP method,
matched route template, response status and elapsed milliseconds. Responses expose
the same ID in `X-Request-ID`. A canonical client-supplied UUID is retained; missing,
malformed or non-canonical values are replaced so untrusted text cannot forge logs.
The application disables Uvicorn's raw-path access logger in every launch mode;
operators must not re-enable it or add proxy request logging that records raw URLs.

On failed API responses, Android reads the correlation header without depending on
HTTP header casing, accepts it only when it is an exact lowercase canonical UUID,
and appends it to the client-owned error message as `Support ID`. It never displays
response bodies or other header values. Missing, uppercase, malformed and
newline-forged identifiers are silently omitted. A user can therefore report one
bounded identifier that operators can correlate with the sanitized completion event.

The logger never records raw paths, query strings, headers, bodies, client IPs,
emails, account IDs, document names/content, answers, provider prompts/responses,
tokens or exception text. Parameterized paths therefore appear as templates such as
`/v1/mastery/sessions/{session_id}`. Unmatched paths use `<unmatched>` rather than
the requested path. Unhandled failures still produce a status-500 completion event
and are re-raised to the application server.

Automated tests verify correlation round-trip, replacement of an injected request
ID, route-template logging, 404 handling, and absence of synthetic secrets from the
serialized event. This provides safe request-rate, latency and status inputs. It is
also live-smoke verified under the QA Uvicorn runner: a request containing a private
query emitted only the `/health` template event and returned the supplied canonical
UUID; no raw access-log line was emitted. It is
not a deployed log sink, retention policy, dashboard, alert, trace system or proof
that a host captures stdout. Production acceptance must configure those controls,
restrict log access, define retention, and alert on actionable error/latency rates.

The API 36 catalog-recovery QA injects a 503, requires a canonical support ID in
the Android dialog, captures `artifacts/qa-support-id.png`, retries successfully,
and completes stale-catalog recovery and disposable-account cleanup. The QA fault
injector preserves the original correlation header when replacing a successful
response with a synthetic failure, matching the production response contract.
