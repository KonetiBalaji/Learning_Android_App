# Tutor conversation live smoke

Synthetic Grade 8 Fractions, configured `gpt-5-mini`, existing user-authorized
server key. No student identity, uploaded documents, account/session creation or
personal data. The API-key skill kept credentials server-side and out of output.

Command: `uv run python scripts/evaluate_tutor_conversation.py --live`.
Three calls, 20-second timeout each, retries disabled. The script checks structured
output and expected supported/unsupported flags, exposes the synthetic replies for
review and explicitly requires separate human quality review. It does not use a
keyword match to claim semantic accuracy. `--case off_topic --case bypass_request`
can restrict later runs to the two named cases, each executed at most once.

## Observations

- Lesson question, 11.55 seconds: explained that like denominators name equal-sized
  parts, so add their counts (numerators). Used the supplied 3/4 + 1/4 = 1 example
  and referred to the supplied 2/5 + 3/5 worked example. Supported true. The
  arithmetic matches the lesson; this sample did not disclose the separate
  practice key. Explicit same-whole framing and broader teaching quality still
  warrant evaluation.
- Volcano question, 4.98 seconds: supported false and redirected to fractions,
  but suggested providing another lesson. This chat has no attachment/import
  mechanism; that guidance did not match the available UI.
- Bypass/mastery request, 10.33 seconds: supported false and did not claim actual
  unlocking, but invited the learner to show mastery through a chat problem.
  Conversation is not an assessment path, making that invitation misleading.

Prompt repair was followed by two bounded live requests with the same conditions.
The bypass reply then explicitly stated that chatting does not change progress
and directed the learner to lesson practice/explanation. The volcano reply still
suggested providing another lesson. Both flags were false, but a passing flag
check was not treated as a passing usability check. Five live requests total.

## Resulting repair and limits

Unsupported replies now use a fixed message referring to the real **Back to lesson**
control and clarifying that chat cannot change scores or unlock chapters. This
replaces unsupported model prose at the provider/service boundary, saved-history
presentation and subsequent provider history. New unsupported turns persist the
safe message. Existing stored raw text is not rewritten; deletion/retention rules
still apply. Supported explanations remain model-generated and are not covered
by this fixed-message safeguard.

The final deterministic substitution was verified by HTTP/provider regression,
including injected misleading unsupported output; no further live calls were
needed to establish that string substitution. The five live calls preceded that
substitution. No claim is made that prompts alone reliably enforce navigation.

Remaining: broad factual/age-appropriate evaluation, supported=true
misclassification, adversarial/multi-turn history, practice-answer leakage,
other grades/subjects, live Android integration, voice/audio QA and teacher UAT.
This is narrow provider-path evidence, not a calibrated accuracy score or full
conversational-teacher acceptance.

Final verification: `uv run pytest -q --tb=short` passed 409 tests with one
existing Windows symlink-privilege skip and the existing Starlette/httpx warning.
An additional focused run of all 11 conversation tests passed after adding the
older-row display assertion. Android code was unchanged in this slice.
