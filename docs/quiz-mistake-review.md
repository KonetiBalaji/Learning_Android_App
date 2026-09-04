# Completed quiz mistake review

The completed document-quiz results response now returns a teaching record for
each answered incorrect question: the prompt and options, the learner's selected
answer, the correct answer, the stored grounded explanation, and source reference.
Android displays all five elements together instead of presenting only the missed
prompt and source label.

The authenticated results query remains owner-scoped. It never includes an
unanswered question or a correctly answered question in `mistakes`, so this change
does not add an answer-key endpoint for an active quiz. Android validates that both
answers belong to the declared options, differ from one another, and have a
nonblank explanation before rendering the review.

**Retry incorrect questions** creates a new owner-scoped quiz containing only the
completed source quiz's incorrect items, in their original order and with fresh
question IDs and no answers. It preserves the original format, difficulty, source
ranges, explanations and references. The source quiz remains immutable. A client
UUID makes response-loss retries return the same retry quiz; a different account
receives 404. Unfinished quizzes and completed quizzes with no mistakes are
rejected without creating data.

Android keeps the retry request UUID until the server response is accepted, then
persists the new active quiz before opening its first question. A process/network
failure can therefore return to the completed results and safely retry the same
operation rather than duplicating a quiz.

Automated tests cover the exact feedback-to-results teaching payload, binary
question-type preservation, malformed client results, incorrect-only copying,
owner denial, unfinished/perfect-result rejection and idempotent replay. This
implements the original results-screen mistake-review and retry-incorrect actions.

The results screen also offers **Configure another quiz**, which revalidates the
same document and returns to its selection/configuration screen, and a bounded
**Increase to Medium/Hard** action. These actions deliberately require the learner
to review the new source selection instead of silently reusing scope that may have
changed or been lost across process restoration. The completed quiz remains in
server history. Mixed and Hard have no automatic next level.

API 36 visual/restart QA, accessibility review and user UAT remain open.
