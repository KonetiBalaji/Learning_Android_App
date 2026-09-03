# Adaptive transition concurrency

Diagnostic, practice and rewrite requests previously read a session, computed an
outcome, then wrote it without checking whether another request had advanced it.
Barrier-synchronized regression tests reproduced two successful writes from the
same snapshot in all three phases.

Before writing attempts or session state, each transition now begins a SQLite
immediate transaction and compares the current phase, question index, correct
count and coaching count with the original snapshot. A missing/changed session
returns 409 and rolls back with no attempt record. The winning transition and its
attempt commit together. Provider work remains outside the short write transaction.
Android requests a fresh saved-session view after an adaptive-screen 409 instead
of repeatedly submitting from stale UI state.

Verification: backend **69 tests passed** on 2026-09-03. The three synchronized
two-request tests now require exactly one 200, one 409, one new attempt and correct
question/coaching counts. Android build/lint and **27 JVM tests passed**; the new
conflict-refresh branch still needs device-level failure injection.

This is not full request idempotency: a delayed retry that reads an already advanced
session is not identified as the same original request. Question/version tokens
and durable request IDs are still needed, as are document-answer concurrency,
multiple-process/load tests, and operational handling of prolonged DB contention.
Overlapping AI requests may still incur both provider calls before one commit is
rejected. No exactly-once billing or full ASM-01 acceptance is claimed.
