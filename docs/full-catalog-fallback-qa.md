# Full Grade 8 fallback journey QA

Status: backend end-to-end QA verified; Android user acceptance and curriculum review
remain open.

An authenticated integration journey traverses the current catalog in its declared
order using deterministic provider mode. For each of the 17 Grade 8 chapters it:

1. starts the real diagnostic HTTP route;
2. verifies that the first public question does not expose its answer;
3. submits each of the chapter's three app-owned correct answers through the real
   answer route;
4. verifies two `next_question` transitions followed by `mastery`;
5. restores the persisted session and verifies `mastered` status.

Catalog order intentionally satisfies Algebra → Geometry, Force and Motion →
Ecosystems, Vocabulary → Writing, and Civics → Economics prerequisites. After all 51
answers, the owner-scoped Grade 8 dashboard must contain exactly 17 chapter rows, each
with `status=mastered` and `mastery=1.0`.

The first test version incorrectly asserted fields from the rewrite response schema
against diagnostic and dashboard responses. It was corrected to the authoritative
contracts (`next_action`, then persisted `status`/`mastery`) without changing runtime
code or weakening the behavioral result.

This journey proves deterministic API continuity, state transitions, persistence,
unlock ordering and aggregate progress for the current catalog. It does not validate
wrong-answer rewrite quality outside the separately reviewed provider path, Android
rendering, board alignment, educator judgment or user UAT.

## Android catalog integration follow-up

On 2026-09-05 the current debug APK was rebuilt with JVM tests, lint and assembly,
then installed on the dedicated `LearnSmart_API36` emulator against the current
deterministic QA-only backend. `scripts/qa-curriculum-catalog.ps1
-ResetTestAppData` passed the real app flow for disposable registration, Grade 8
selection, all four subject lists from Fractions through Economics, return navigation,
Grade 9 disabled behavior, process-stop/restart restoration, and safe retirement of a
local resume pointer after the server session was marked with a legacy catalog version.
The disposable account was deleted and app data cleared by the harness.

The Grade availability, current subject dashboard and post-migration subject dashboard
screenshots were inspected. Grade cards, four subject cards, catalog identity, progress
and parent/teacher actions were readable without visible overlap or clipping at the
tested 1080 × 2400 emulator size. The latter two captures are expected to show the same
restored subject screen because successful recovery returns to the current catalog.

This is installed-app API 36 integration evidence, not physical-device testing,
spoken-accessibility review, curriculum approval or user acceptance.

## Android deterministic-content rendering follow-up

On 2026-09-05 `scripts/qa-deterministic-diagnostics.ps1
-ResetTestAppData` installed the current debug APK on `LearnSmart_API36` and opened
one production deterministic fallback diagnostic in each subject: Mathematics /
Decimals, Science / Cells and Living Things, English / Grammar, and Social Studies /
Geography. The harness asserted the exact first prompt and correct option returned by
the app-owned banks, captured each screen, deleted each disposable account, and
cleared app data.

All four captures were visually inspected at 1080 × 2400. The subject/chapter
identity, question, answer options, progress, teacher state and disabled submit action
were readable without visible overlap or clipping. This proves representative
installed-app rendering of the real fallback content, not all 51 screens, physical-
device coverage, curriculum approval or user acceptance.
