# Document answer submission

`POST /v1/quizzes/{quiz_id}/questions/{question_id}/answer`

The authenticated owner submits `selected_option` from the public options.
Question IDs are stable for the lifetime of a quiz. Answers are immutable.

- First valid submission for the earliest unanswered question: 200 Feedback.
- Identical retry for an answered question: 200 with the original feedback,
  without changing the saved answer or timestamp.
- Different answer for an already answered question: 409, no mutation.
- Answering a later question while an earlier question is unanswered: 409.
- Invalid option on an unanswered question: 422.
- Unknown question/quiz or another owner's question: 404; missing auth: 401.

The read/validation/write sequence uses a short SQLite immediate transaction.
Concurrent identical requests can both receive 200 but produce one saved answer;
concurrent different choices produce one 200 and one 409. No AI calls occur inside
this transaction. A prolonged database lock can still fail the request; production
load/contention handling requires further verification.

Replayed Feedback keeps the original subsequent question, even if another device
has since advanced. Use `GET /v1/quizzes/{id}` for the current resume position.
This question-level replay does not provide idempotent quiz creation or adaptive
mastery submission, and does not automatically fix legacy out-of-order answers.
