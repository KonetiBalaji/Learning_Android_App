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
