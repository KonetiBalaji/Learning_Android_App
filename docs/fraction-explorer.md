# Interactive equal-part fraction model

The Mathematics/Fractions tutor now includes a native interactive model. Learners
can vary the shared denominator from 2 to 12 and each numerator from zero to one
whole. Equal-width bars show both operands and up to two result wholes. The text
shows the unreduced sum, simplified fraction, whole count and remainder. Reducing
the denominator clamps existing numerator selections to the new range; Reset
restores 3/4 + 1/4. The controls use saveable Compose state and semantic labels.

Exploration makes no API calls and never changes assessment/mastery evidence. It
is explicitly separate from answering a question. This component was implemented
locally, not ported from OpenMAIC, and must not be counted as another upstream
adaptation. It teaches equal-denominator addition only, not unlike-denominator
operations or every Grade 8 concept.

Android build/lint and **27 JVM tests passed** on 2026-09-03. Five model tests cover
zero, simplified fractions, one/two wholes, input validation, denominator changes,
and exhaustive supported arithmetic combinations. Device interaction evidence is
recorded separately; saveable-state restoration, both themes, screen/font sizes
and TalkBack navigation need dedicated testing before broad accessibility claims.

API 36 emulator interaction: dragging the first numerator changed 3/4 to 0/4,
updated the sum to 1/4, and Reset restored 3/4 + 1/4 = 1. Screenshot
`artifacts/qa-fraction-model.png` was inspected for bars, labels and layout.
The first automated tap missed the slider's active track; a direct drag confirmed
the control worked, and the repeatable script was corrected to scroll fully into
view and drag inside the track. This is one-device interaction evidence.
