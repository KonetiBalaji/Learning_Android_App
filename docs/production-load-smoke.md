# Production-shaped concurrent smoke

`backend/scripts/production_load_smoke.py` is a dependency-free deployment check.
It creates one disposable learner, then issues a bounded mix of authenticated account,
catalog, progress, weekly-report and retention reads plus serialized interest writes.
Readiness is sampled during the same workload. Every response status and selected
identity/schema invariant must pass; the final account state must remain consistent.
There are no retries, so transient HTTP, timeout, JSON, authentication or database
contention failures fail the run.

The command permits 20–5,000 requests and 2–100 workers. It prints request count,
duration, throughput, p50, p95 and maximum latency. Metrics are observations rather
than acceptance thresholds because the hosted runner is not the selected production
hardware.

Run from `backend`:

```powershell
uv run python scripts/production_load_smoke.py https://confirmed-host.example --requests 700 --concurrency 20
```

The GitHub `backend-container` job runs 700 requests with concurrency 20 against the
same freshly built locked image used for non-root/read-only-filesystem readiness QA.
The runtime volume and disposable account are destroyed with that CI container.

Local HTTP QA passed 701 total responses with zero failures on 2026-09-04. The first
run correctly failed because the fixture supplied interests outside the app allowlist;
the fixture was corrected rather than relaxing validation. The repeat completed in
2.258 seconds at 309.95 requests/second, with p50 51.3 ms, p95 164.52 ms and maximum
373.91 ms on this machine.

This is a modest single-instance correctness smoke under contention. It does not
establish user capacity, an SLO, multi-worker behavior, long-duration soak behavior,
reverse-proxy limits, WAN/mobile latency, provider-call capacity or production-host
monitoring. Those require the confirmed deployment and budget.
