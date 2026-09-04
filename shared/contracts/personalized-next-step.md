# Evidence-based personalized next step

`GET /v1/progress/dashboard?grade={grade}` derives focus areas only from independent
diagnostic and rewrite evidence. Guided practice is coaching and never creates or
clears a weak area. Consecutive unresolved mistakes for the same grade, subject,
chapter and normalized concept are counted; the latest successful independent
assessment clears that sequence.

The response retains the concise `weak_areas` list and adds structured
`weak_area_evidence` with the grade, subject, chapter and unresolved independent
mistake count. Recommendations prioritize the most recent unresolved evidence and
name its catalog subject/chapter and count. With no unresolved evidence, the next
step is the latest incomplete session, otherwise the first unmastered catalog
chapter whose prerequisite is mastered. A new learner therefore receives a concrete
first diagnostic rather than a generic instruction. Aggregate all-grade requests do
not invent a grade-specific starting point.

The state is account- and grade-scoped and uses the server catalog order and
prerequisite graph. It is deterministic guidance, not an AI prediction or proof of
learning. Backend tests cover recurrence, remediation clearing, active-session
continuation, new-learner selection, grade separation and owner isolation. API 36 QA
uses a disposable account to create two independent mistakes, verifies the exact
evidenced recommendation in the Android report, submits a successful practice and
rewrite through the API, reloads the report, and verifies the focus clears in favor
of the active diagnostic. Screenshots are untracked QA evidence.
