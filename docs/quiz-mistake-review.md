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

Automated tests cover the exact feedback-to-results teaching payload, binary
question-type preservation, and rejection of malformed client results. This
completes the original results-screen mistake-review content requirement. Retry
incorrect questions and another-quiz configuration are separate actions and
remain open, as do API 36 visual QA, accessibility review and user UAT.
