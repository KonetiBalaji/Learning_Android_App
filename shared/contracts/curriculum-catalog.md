# Versioned server curriculum catalog

## Contract

`GET /v1/catalog?grade=8` is authenticated and accepts grades 1 through 12. It
returns a version, the requested grade, an explicit board-alignment state, and an
ordered subject/chapter graph. The current version is `foundation-2026-09` with
board `unconfirmed`. It contains the existing 17 foundation topics across
Mathematics, Science, English and Social Studies, including each of the four
existing immediate prerequisites.

This is a product catalog, not an authoritative national, state or examination-
board curriculum. The same foundation topic set is currently exposed for each
grade and provider prompts receive the selected grade for age adaptation. This
preserves the original Grades 1–12 navigation without pretending that the chapter
set has been validated for every grade. Board-specific replacement and educator
review remain CUR-01 acceptance gates.

The backend now rejects a diagnostic subject/chapter pair that is absent from this
catalog before selecting or calling any AI provider and before creating a session.
This prevents invented client identifiers from consuming provider work. The
prerequisite map is derived from the same catalog objects rather than independently
duplicating locked chapter identifiers.

## Android behavior

Android no longer owns subject titles or chapter lists. It maps the four allowlisted
subject IDs only to local icon/color presentation, validates the complete response,
and renders server titles, ordering and prerequisite locks. It rejects wrong-grade,
unknown-board, reordered/unknown-subject, missing chapter-map, blank, or duplicate
chapter responses. There is no static chapter fallback.

Catalog and progress load together after grade selection, authenticated restart and
explicit progress refresh. Changing grade clears the prior catalog before network
work, so failure cannot display stale choices for another grade. Resuming a mastery
session reloads the catalog for the session's saved grade before mapping its subject
and chapter. Every mastery session stores and returns the catalog version that
created it. If that version differs from the current catalog, Android removes only
the local resume pointer, retains the server record, returns to the current subject
catalog, and tells the learner to start a new diagnostic. It never maps an older
question snapshot onto current curriculum navigation. Returning from a document
flow requests the catalog when none is held.

## Verification and limits

Backend tests verify authentication, boundary grades, version/board/order, 17 unique
chapters, valid prerequisite ordering, normalized known lookup, pre-provider
rejection of unknown identifiers, legacy database migration, and session-version
retention after a catalog change. Android tests verify strict response invariants.
The full backend regression passed 456 tests with one existing Windows skip;
Android passed 133 JVM tests with zero failures/skips plus lint and debug assembly.
On API 36, `scripts/qa-curriculum-catalog.ps1 -ResetTestAppData` loaded Grade 8,
opened all four subject lists and checked their first and last chapters, restarted
the process, and verified the versioned catalog returned. It then changed to Grade
9 while injecting a one-shot 503, verified the Grade 8 subject graph was absent,
displayed a safe unavailable state with an explicit refresh action, recovered all
four subjects, restarted, and verified the recovered catalog returned. The
disposable account was deleted and app data cleared.

The inspected `artifacts/qa-curriculum-catalog.png` shows all four subject cards and
the catalog/board disclosure without clipping. The inspected
`artifacts/qa-curriculum-catalog-failure.png` shows the Grade 9 fail-closed state and
large refresh control without clipping. The inspected
`artifacts/qa-curriculum-catalog-migration.png` shows the current catalog after the
incompatible local pointer was retired; the harness also authenticated a direct
read proving the legacy-version server session still existed before account cleanup.
All three are untracked QA evidence. Physical-device accessibility, authoritative
curriculum data and UAT remain open.
