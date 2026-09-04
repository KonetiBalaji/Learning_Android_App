# Algebra balance explorer

The Grade 8 Mathematics `algebra` tutor route includes a native equation-balance
explorer for `2x + 3 = 11`. The learner controls four stages: starting equation,
subtracting 3 from both sides, dividing both sides by the same nonzero number, and
substituting `x = 4` into the original equation. Each stage explains why equality is
preserved. The equation has a concise accessibility description. Exploration cannot
submit an assessment response or change mastery.

JVM tests verify the ordered operations, both displayed sides and final substitution
evidence. API 36 component and full tutor-journey tests render the explorer, apply
the first balance operation and verify unchanged mastery. Manual TalkBack traversal,
broader algebra coverage, curriculum alignment, physical-device QA and UAT remain open.

This follows the fixed native action/content pattern recorded as OA-03 in
`openmaic-provenance.md`. The operations and equations are trusted app-owned values;
no generated action, HTML, script or OpenMAIC source code is executed or copied.
