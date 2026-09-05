# Versioned server curriculum catalog

## Contract

`GET /v1/catalog?grade=8` is authenticated and currently accepts Grade 8 only. It
returns a version, the requested grade, an explicit board-alignment state, and an
ordered subject/chapter graph. The current version is `foundation-2026-09` with
board `unconfirmed`. It contains the existing 17 foundation topics across
Mathematics, Science, English and Social Studies, including each of the four
existing immediate prerequisites.

This is a product catalog, not an authoritative national, state or examination-
board curriculum. Grades 1-7 and 9-12 are planned expansion, but the backend
rejects their catalog and diagnostic requests with 422 before provider selection
or session creation. This prevents the Grade 8 foundation set from being
misrepresented as reviewed material for another grade. Board-specific replacement
and educator review remain CUR-01 acceptance gates.

The backend now rejects a diagnostic subject/chapter pair that is absent from this
catalog before selecting or calling any AI provider and before creating a session.
This prevents invented client identifiers from consuming provider work. The
prerequisite map is derived from the same catalog objects rather than independently
duplicating locked chapter identifiers.

## Android behavior

Android displays all twelve grade choices, marks Grades 1-7 and 9-12 as coming
later, and disables them. Grade 8 is the only selectable and restorable grade.
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

Backend tests verify authentication, rejection of unsupported grades before provider
work, version/board/order, 17 unique
chapters, valid prerequisite ordering, normalized known lookup, pre-provider
rejection of unknown identifiers, legacy database migration, and session-version
retention after a catalog change. Android tests verify strict response invariants.
The full backend regression passed 634 tests with one existing Windows skip;
Android passed 176 JVM tests with zero failures/skips plus lint and debug assembly.
On API 36, `scripts/qa-curriculum-catalog.ps1 -ResetTestAppData` loaded Grade 8,
opened all four subject lists and checked their first and last chapters, restarted
the process, and verified the versioned catalog returned. It then changed grade,
verified Grade 9 was visibly marked coming later and disabled, confirmed tapping
it did not leave grade selection, selected Grade 8 again, restarted, and verified
the catalog returned. The
disposable account was deleted and app data cleared.

The inspected `artifacts/qa-curriculum-catalog.png` shows all four subject cards and
the catalog/board disclosure without clipping. The inspected
`artifacts/qa-grade-availability.png` shows the honest Grade 8 launch boundary. The inspected
`artifacts/qa-curriculum-catalog-migration.png` shows the current catalog after the
incompatible local pointer was retired; the harness also authenticated a direct
read proving the legacy-version server session still existed before account cleanup.
All three are untracked QA evidence. Physical-device accessibility, authoritative
curriculum data and UAT remain open.
