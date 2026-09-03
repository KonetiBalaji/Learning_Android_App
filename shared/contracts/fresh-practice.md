# Fresh Fractions practice

Android now opts into fresh practice with `fresh_practice: true` on practice
submission, alongside its existing expected-state token. On an incorrect answer
in Mathematics/Fractions, the backend can produce a new variant for the exact
existing concepts Adding like fractions, Subtracting like fractions and Equivalent
fractions. Numerators/denominators are generated arithmetically from the coaching
round, not by an AI provider. Expected results are calculated as fractions; adding
and subtracting accept the raw or simplified result. Equivalent-fraction questions
require the specified denominator. This is not a general symbolic answer grader.

The submitted attempt retains its original prompt. The next practice prompt,
answer key and hint are committed with the coaching/state transition and persisted
tutor lesson. `next_practice` contains the public tutor lesson, never the answer
key. Resume returns that same lesson, and a stale expected-state retry is rejected
without rotating again. Correct practice advances to rewrite without producing a
new question or directly granting mastery. Legacy requests without the opt-in keep
their existing question, so old clients do not unknowingly grade against a new one.

Android decodes the next lesson before accepting the state token, displays its
question/hint and keys the answer field to session/prompt so the previous response
is cleared when the question changes. The feedback asks the learner to review the
question currently shown. Other subjects and unmatched concept names retain the
existing behavior; validated general practice generation remains outstanding.
Failed rewrite remediation does not yet generate another fresh variant.

Verification: 188 backend tests and Android debug build/lint/71 JVM tests passed.
New tests verify 30 distinct arithmetic variants for each of the three concepts,
persisted resume, original attempt history, stale retry rejection, correct next
answer progression and unchanged legacy behavior. No live AI requests were made.
Device wrong-answer/new-question/restart behavior, broader concept coverage,
difficulty calibration and educator/user acceptance remain open. TUT-02 is partial.
