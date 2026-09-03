# MVP runtime architecture

```text
Android Compose client
  │ bearer token + multipart document
  ▼
FastAPI boundary
  ├─ local account and signed-token authentication
  ├─ file validation, extraction, and chapter detection
  ├─ document and quiz ownership checks
  ├─ source-grounded question construction and answer evaluation
  └─ SQLite metadata + local file store (development only)
```

The API never returns a question's correct option before the learner submits an answer. It verifies that the selected option belongs to the question, records one attempt, then supplies correctness, explanation, source reference, and the next question.

The grade-and-subject mastery path uses the same server-owned boundary:

```text
Start diagnostic
  → correct: next diagnostic question
  → incorrect: age-appropriate tutor explanation
      → guided practice
      → explanation in the student's own words
      → mastery or another coaching round
  → persisted progress dashboard and chapter unlock signal
```

Diagnostic, practice, and rewrite attempts are stored against an authenticated owner. A later AI provider may generate explanations and practice variants, but it must return the existing structured contracts and pass the same server-side validation before content reaches Android. Remediation is treated as new evidence: a learner can achieve mastery after initially answering incorrectly.

For local MVP operation the question generator uses deterministic sentences drawn from the selected chapter. This permits the full verified learning loop without placing an LLM credential in the app. A production LLM provider must remain behind the server-side validation boundary and retain the same structured question, grounding, duplicate-detection, and answer-validation contract.
