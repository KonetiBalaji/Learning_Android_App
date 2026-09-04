# Grade 8 Geography coordinate explorer

## Scope

The exact `Grade 8 -> Social Studies -> Geography` tutor route now includes a
native globe model. A learner can select the Equator, Prime Meridian or an example
coordinate. The diagram highlights the corresponding zero-degree line or places a
point at 20° N, 60° E, then explains the reference and a direction check.

The three actions, labels and drawing instructions are application-owned Kotlin.
The app does not execute provider-authored HTML/JavaScript, model tool calls,
arbitrary coordinates or upstream action payloads. The Canvas exposes a changing
accessibility description, and every selection has an explicit full-width text
button. Exploration is local UI state and cannot submit an answer, add coaching or
award mastery.

## Verification

`scripts/qa-map-explorer.ps1 -ResetTestAppData` ran against the dedicated
`LearnSmart_API36` emulator and explicitly isolated `scripted-social-qa` fixture.
The journey created a disposable account, selected Grade 8 Social Studies
Geography, entered tutoring after a known wrong answer, verified the initial
Equator state, selected Coordinates, and verified the latitude-first explanation
and north/east interpretation. An authenticated session read proved `tutor` state,
zero coaching rounds and zero mastery score. The account was deleted and app data
cleared.

The inspected `artifacts/qa-map-explorer.png` clearly shows both reference lines,
the selected coordinate marker, all selector labels, the explanatory copy and the
next practice action without overlap. It remains untracked QA evidence and is not
packaged in the APK.

Unit tests verify the exact route, canonical zero-degree labels and latitude-before-
longitude ordering. Android verification passed 130 JVM tests with zero
failures/skips plus lint and debug assembly. Backend regression remained 451
passing with one existing Windows skip. Fixture and PowerShell syntax checks passed.

## Limits

This simplified diagram teaches reference-line and coordinate ordering. It is not
a geographically projected map and does not calculate or validate arbitrary
coordinates. It does not establish curriculum-board alignment, educator review,
TalkBack traversal quality, physical-device behavior, UAT, or coverage for other
Social Studies chapters. TUT-05 remains partial.
