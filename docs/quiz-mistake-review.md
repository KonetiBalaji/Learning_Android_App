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

At this stage API 36 visual/restart QA, accessibility review and user UAT remained
open; the following journey closes the API 36 portion only.

## API 36 result-action journey

`scripts/qa-document-recovery.ps1 -ResetTestAppData -VerifyResultActions`
passed on the dedicated `LearnSmart_API36` emulator with the isolated deterministic
QA backend. The disposable learner uploaded through Android's real document picker,
restored selection and quiz state after process stops, and reached a completed
ten-question result.

The app displayed a complete mistake teaching record and all five actions. It
created a seven-question mistake-only retry, persisted a different active quiz ID,
cleared the pending retry UUID, exposed zero answered retry items, and restored its
first question after force-stop. The QA client completed only the remaining answers
through the public API. Android then revalidated the document through **Configure
another quiz**, generated another ten-question quiz, returned to results, and
persisted **Medium** after tapping **Increase to Medium**.

`artifacts/qa-document-result-actions.png` and
`artifacts/qa-document-increased-difficulty.png` were visually inspected. The
mistake answer/explanation/source and action labels are readable; the second frame
shows Medium selected. Generated captures remain untracked. This is deterministic
emulator QA, not live-provider quality, physical-device accessibility or user UAT.

The journey was repeated with the emulator's installed TalkBack service temporarily
enabled on the results screen. Its active accessibility tree exposed one complete
mistake teaching record and all five actions: retry incorrect, configure another,
increase difficulty, study another document, and return to the learning path. The
runner restored the original disabled service state and notification permission in
`finally`; post-run inspection confirmed no enabled accessibility service,
`accessibility_enabled=0`, and TalkBack notification access denied. This proves
node exposure on the API 36 emulator, not spoken traversal order, gesture-only use,
switch access, a physical device, or user acceptance.
