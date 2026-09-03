# Server-enforced chapter prerequisites

The existing Android catalog marks these four chapters as locked. The backend
now enforces the same immediate prerequisites on `POST /v1/mastery/diagnostics`:

| Subject | Locked chapter | Required chapter |
| --- | --- | --- |
| math | geometry | algebra |
| science | ecosystems | force-and-motion |
| english | writing | vocabulary |
| social | economics | civics |

The prerequisite's latest session must have server status `mastered`, for the
same owner, grade and subject. Another account or grade cannot grant access.
An unfinished newer attempt does not inherit an older mastery result, matching
the existing latest-session progress policy. Ties in `started_at` use descending
SQLite row ID, also applied to progress dashboard selection. Subject/chapter
matching is case-insensitive, consistent with stored normalized identifiers.

A missing prerequisite returns 403 before calling a provider. The condition is
checked again inside the session-insert transaction after generation, without
holding a database write lock during provider work. If eligibility changed,
the request returns 403 and no target session is inserted. A provider call can
already have occurred in that race. Previously created sessions remain resumable;
this does not revoke or delete learning history.

These are the current app's four gates, not a complete or authoritative curriculum
dependency graph. Other existing chapters remain open. The country/board-specific
path, time-spent reporting, and a server-supplied catalog remain outstanding.
Mastery quality is still subject to the separate assessment acceptance gates.

Verification: all 180 backend tests passed. Five new tests cover all four gates,
owner/grade isolation, absent and partial mastery, same-timestamp latest attempts,
case normalization, no provider call when denied, and eligibility changing during
provider generation without a target session being saved. A fixture provider was
used; its fraction questions are not claimed as real geometry or other chapter
content. No live AI calls occurred. Android gate-denial/device behavior and
curriculum-specific UAT remain unverified.

## Server-owned unlock display

`GET /v1/progress/dashboard?grade=8` now includes `grade` and
`unlocked_chapter_ids`, with subject-qualified values such as `math:geometry`.
These are the eligible gated chapters, not an exhaustive list of open chapters.
They use the same prerequisite map and latest-session status as diagnostic
enforcement. An aggregate dashboard without a grade returns an empty unlock list;
cross-grade mastery cannot be interpreted as access for a particular grade.

Android no longer infers unlocks from local chapter ordering. It accepts only
the server list for the requested grade. Legacy/missing scope grants no new
unlocks; a mismatched explicit grade or malformed/duplicate identifiers rejects
the response. Open chapters remain open. A stale previously loaded decision may
still be displayed after a failed refresh, but the backend rechecks every new
diagnostic request. Existing sessions remain resumable as above.

Backend 180 tests and Android debug build/lint/66 JVM tests passed. Tests assert
the four unlock lists, latest-attempt relocking, grade-scoped versus aggregate
responses, client wrong-grade rejection and legacy fail-closed behavior. Actual
device unlock transitions and stale-screen denial remain pending. No live AI
requests were made. This does not supply an authoritative curriculum catalog.
