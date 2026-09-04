# Privacy-safe request observability

Every backend HTTP completion now emits one structured JSON log event through the
`learning.http` logger. The event contains only a UUID request ID, HTTP method,
matched route template, response status and elapsed milliseconds. Responses expose
the same ID in `X-Request-ID`. A canonical client-supplied UUID is retained; missing,
malformed or non-canonical values are replaced so untrusted text cannot forge logs.

The logger never records raw paths, query strings, headers, bodies, client IPs,
emails, account IDs, document names/content, answers, provider prompts/responses,
tokens or exception text. Parameterized paths therefore appear as templates such as
`/v1/mastery/sessions/{session_id}`. Unmatched paths use `<unmatched>` rather than
the requested path. Unhandled failures still produce a status-500 completion event
and are re-raised to the application server.

Automated tests verify correlation round-trip, replacement of an injected request
ID, route-template logging, 404 handling, and absence of synthetic secrets from the
serialized event. This provides safe request-rate, latency and status inputs. It is
not a deployed log sink, retention policy, dashboard, alert, trace system or proof
that a host captures stdout. Production acceptance must configure those controls,
restrict log access, define retention, and alert on actionable error/latency rates.
