# Observed study time

`POST /v1/mastery/sessions/{id}/presence` requires the session owner's bearer
token. The response contains `session_id` and integer `observed_study_seconds`.
The server uses its own observation time; client-supplied duration is not used.
This measures observed presence, not proof of attention, learning or mastery.

The first observation establishes a cursor and credits zero. Consecutive
observations for the same session credit the elapsed interval only when the gap
is at most 60 seconds. Longer gaps are dropped entirely. One owner-level cursor
prevents overlapping credit across sessions, grades or devices: switching sessions
establishes a new cursor without crediting the gap. Duplicate/backward timestamps
cannot rewind the cursor or create additional time. All updates run in one write
transaction; no provider call is involved.

An observation after completion may close the preceding short interval only up
to the server's completion timestamp. Further calls cannot accrue completed time
or displace a different ongoing session. Intervals retain fractional seconds;
the response truncates their summed total to whole seconds. Missing/other-owned
session returns 404; invalid/deleted authentication returns 401. Session/account
deletion cascades to presence and interval records.

Verification: 183 backend tests passed, including sequential and duplicate
observations, clock rollback, long gaps, cross-grade session switching, no interval
overlap, completion clipping, ownership, ignored client durations and deletion.
Existing databases receive the two additive tables during normal initialization.
No historical duration is inferred from session start/end timestamps.

Android foreground/input-idle signals, lifecycle stop/start handling, heartbeat
retry behavior, session/weekly displays and device QA remain to be implemented.
Do not label current sessions as time-tracked yet. Background/idle suppression
depends on that client integration. Even then, a modified client could continue
sending observations while unattended; the metric must remain clearly labeled.
Production retention, request-rate limits and interval compaction are also open.

## Reporting totals

The progress dashboard and weekly report now return `observed_study_seconds`.
Dashboard totals sum stored interval durations for the owner and optional grade.
Weekly totals use only the overlap between each interval and the report's exact
rolling seven-day `[period_start, period_end)` window. They do not assign the
entire interval to the day it ended. Fractional seconds are summed before the
total is truncated, and empty/untracked history contributes zero, not an estimate
derived from historical session age. Omitting grade aggregates only this owner's
grades; another owner's intervals never contribute.

All 184 backend tests passed. The new integration test covers intervals crossing
both weekly boundaries, intervals fully outside the window, grade-specific versus
aggregate totals, empty grades and other-owner exclusion. Android presence
emission and the time display are still not connected; this is report infrastructure,
not evidence that real foreground study has been measured or accepted in UAT.
