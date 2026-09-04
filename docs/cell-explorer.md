# Grade 8 Cells interactive explorer

## Scope and learning boundary

The tutor screen now exposes a native interactive cell diagram only for the exact
`Grade 8 -> Science -> Cells and Living Things` lesson route. Learners can select
Nucleus, Mitochondrion or Ribosome, see the matching structures highlighted, and
read a curated function and evidence statement. Fractions keeps its existing
interactive model; unsupported subject/chapter pairs do not receive a generic or
mislabelled scene.

Selection is local presentation state. It does not call the API, submit an answer,
advance a question, add coaching rounds or change mastery. The Canvas has a dynamic
accessibility description naming the highlighted organelle, and every selection is
also represented by a full-width text button.

All learner-visible content and drawing commands are application-owned Kotlin. No
model response, HTML, JavaScript, coordinate command or upstream action payload is
executed on the device. This deliberately narrows OpenMAIC's general action/highlight
idea to an allowlisted scene whose instructional content can be reviewed and tested.

## Verification

`scripts/qa-cell-explorer.ps1 -ResetTestAppData` ran against the dedicated
`LearnSmart_API36` emulator and the explicitly isolated `scripted-science-qa`
backend. The journey created a disposable account, selected Grade 8 Science Cells,
entered tutoring after a known wrong diagnostic answer, changed the selection from
Nucleus to Mitochondrion, and verified the expected function text. A server read
then proved the session remained in `tutor` with zero coaching rounds and zero
mastery score. The account was deleted and app data cleared.

`artifacts/qa-cell-explorer.png` was visually inspected. All three selector labels,
the selected state, highlighted mitochondria, function/evidence copy, and the next
practice control are legible without overlap. The capture is QA evidence and remains
untracked; it is not shipped in the APK.

Unit coverage verifies exact-route allowlisting and three distinct instructional
entries. Android verification passed 128 JVM tests with zero failures/skips plus
lint and debug assembly. The backend regression passed 444 tests with one existing
Windows skip. The PowerShell device harness parses without errors.

## Known limits

This is a three-organelle explanatory model, not a complete cell-anatomy simulator.
It does not establish curriculum-board alignment, factual review by an educator,
TalkBack traversal quality, physical-device behavior, UAT acceptance, or interactive
coverage for the remaining chapters and subjects. TUT-05 therefore remains partial.
