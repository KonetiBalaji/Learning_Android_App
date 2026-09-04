# Legacy premature-mastery repair

Status: implemented and regression tested. Production migration rehearsal and
operator review remain pending.

Before 2026-09-03, a successful concept rewrite could mark a chapter mastered
even when later questions in its persisted diagnostic bank had not been answered.
Current mastery transitions require `current_question == len(questions_json)`.

During schema initialization, the application now examines only sessions already
marked `mastered`. If a valid, non-empty persisted question-bank array contains a
later unanswered position, the session is reopened as `diagnostic` at its existing
`current_question`; `completed_at` is cleared. Question content, attempts, scores,
owner, grade and position are not rewritten. A valid completed mastery is unchanged.
Blank, malformed or non-array legacy banks are not guessed at automatically and
must be reviewed before importing such a database into production.

Every automatic correction creates one idempotent `mastery_session_repairs` row
with repair kind `premature-mastery-v1`, previous status, previous completion time
and repair time. The row is owned transitively through the session and is deleted
when that session or account is deleted. Repeated startup does not create another
record or move the learner again.

Before production cutover, restore a copy of the candidate backup in an isolated
environment, start the candidate revision, and review:

```sql
SELECT session_id, repair_kind, previous_completed_at, repaired_at
FROM mastery_session_repairs
ORDER BY repaired_at, session_id;
```

Confirm that each listed learner resumes at the next unanswered diagnostic item,
then run the normal backup verification and UAT journeys. Retain the pre-migration
backup through the approved rollback window. This migration does not establish a
production backup destination, retention approval or user acceptance.
