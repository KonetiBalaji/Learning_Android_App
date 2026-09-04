# Fresh practice

## Reviewed general generation

For provider-backed Grade 8 lessons outside the deterministic Fractions path,
fresh practice now has no fixed round limit. The server asks for one new,
objective, age-suitable question grounded in the current verified concept and
method. It supplies up to the last 20 practice prompts to discourage repetition
and may use saved learner interests only as an optional hypothetical context.

A separate model call independently solves the question without receiving the
generator's proposed answer or hint. It returns a bounded set of justified answer
variants and checks ambiguity, topic and grade suitability. The server rejects
repeated prompts, failed review, generator/reviewer key disagreement and hints
that contain a reviewed textual answer. Numeric equivalence is enabled only when
the blind reviewer finds no requested representation; explicit format wording
still forces exact matching. Only the blind reviewer's accepted answers are saved.

Generation and review happen before the existing transactional state check. The
new prompt, private key, hint and public lesson are committed together only if
the learner is still on that practice state. Resume returns the same prompt and
a stale retry cannot rotate again. If generation, parsing or review fails, the
resilient provider returns no replacement and the existing question remains;
Fractions continue to use their deterministic arithmetic generator.

Backend regression includes blind-payload isolation, exact and numeric agreement,
singular/plural variants, repetition, invalid review, key disagreement,
answer-leaking hints, outage behavior and a non-Fractions HTTP/database flow.
A 2026-09-04 live smoke with the approved existing key accepted one Cells variant
and one English subject-verb-agreement variant after independent review. An
earlier disagreement was rejected. This is narrow development evidence, not an
unlimited-content guarantee, curriculum-board alignment, broad factual accuracy,
educator review, UAT or production availability. Provider cost/latency controls
and larger holdout evaluation remain open.

## Deterministic Fractions generation

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
Rejected rewrite remediation is covered by the later implementation and evidence below.

Verification: 188 backend tests and Android debug build/lint/71 JVM tests passed.
New tests verify 30 distinct arithmetic variants for each of the three concepts,
persisted resume, original attempt history, stale retry rejection, correct next
answer progression and unchanged legacy behavior. No live AI requests were made.
Device wrong-answer/new-question/restart behavior, broader concept coverage,
difficulty calibration and educator/user acceptance remain open. TUT-02 is partial.

## API 36 repeated-practice device evidence

`scripts/qa-mastery-resume.ps1 -ResetTestAppData -VerifyFreshPractice
-VerifyWeeklyReport` passed on LearnSmart_API36 with the isolated backend. Android
submitted two wrong practice answers, each produced a distinct saved prompt/hint,
the old input cleared, and force-stop/restart restored each variant without changing
the server state token. The inspected `artifacts/qa-fresh-practice.png` shows the
second variant `4/11 + 2/11` with an empty answer field. The script computed `6/11`
from the displayed operands, submitted it through Android, and advanced to rewrite.

The general explanation used for QA now states that adding numerator parts keeps
the denominator unchanged, without incorrectly claiming every sum makes one whole.
Question 2 restart and completion of all remaining diagnostics passed. The weekly
report recorded seven responses (including the two wrong practice attempts) and
one unique mastered chapter. No duration or answer-key fixture injection was used
for these new practice answers, and there were no live AI calls.

This verifies the addition workflow only. Subtraction/equivalence device flows,
post-commit practice response loss, other subjects, fresh failed-rewrite coaching
and educator/UAT acceptance remain open. Backend arithmetic coverage does not
prove those untested device or curriculum outcomes.

## Fresh practice after a rejected explanation

Android now also sends `fresh_practice: true` on rewrite submission. When grading
rejects an explanation for one of the supported Fractions concepts, the backend
creates the next arithmetic variant and saves its answer key, prompt and hint in
the same transaction as the assessment/coaching transition. It preserves the
grader's coaching explanation and returns the public lesson in `next_practice`.
The phase returns to tutor without incrementing question progress or mastery.

Android decodes the complete next lesson before accepting the response state token
and uses it instead of merely replacing the old explanation. Resume returns the
same stored lesson. Legacy requests keep the old practice question. Unavailable
grading still returns without a saved assessment or a changed question. Other
subjects and unmatched concept names retain their existing behavior.

190 backend tests and Android build/lint/71 JVM tests passed. New opt-in/legacy
tests verify rejected grading does not award mastery, coaching/variant persistence,
stale rewrite rejection and acceptance of the fresh question's correct answer.
No live AI requests were made. The failed-rewrite device flow, response-loss
injection, general subject coverage and educator/UAT evaluation remain open.

## API 36 rejected-rewrite device evidence

`scripts/qa-mastery-resume.ps1 -ResetTestAppData -VerifyFreshPractice
-VerifyRejectedRewrite -VerifyWeeklyReport` passed against the isolated scripted-QA
backend on LearnSmart_API36. After two wrong practice cycles and a correct answer,
Android submitted `I do not know`. The rejected explanation returned to tutoring
without advancing mastery, with a new saved question and coaching. Force-stop and
restart preserved that lesson and its state token. The inspected screenshot
`artifacts/qa-rejected-rewrite.png` shows `5/13 + 2/13` and an empty answer field.
The computed answer `7/13` submitted through Android returned to rewrite.

A valid explanation then advanced to question 2; restart and all remaining
diagnostics passed before mastery was awarded. The weekly report matched nine
learning responses and one unique mastered chapter. This is deterministic addition
workflow QA, not a live-provider grading-quality test or user acceptance. Other
concepts on-device, response loss, general subject coverage and educator/UAT
evaluation remain open.
