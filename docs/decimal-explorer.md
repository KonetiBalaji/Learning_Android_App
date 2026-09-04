# Decimal place-value explorer

The Grade 8 Mathematics `decimals` tutor route includes a native, learner-controlled
place-value explorer for `42.375`. Selecting tens, ones, tenths, hundredths or
thousandths highlights the corresponding digit and displays its exact positional
value and multiplication check. Its accessibility description names the full number,
selected digit and selected place. Exploration cannot submit an assessment response
or change mastery.

JVM tests verify the catalog route, all five digit indexes, place names, values and
instructional checks. Android JVM tests, lint and debug assembly pass. This evidence
does not establish rendered-device interaction, TalkBack traversal, broader decimal
concept coverage, curriculum alignment, physical-device QA or UAT.

This follows the bounded native action/highlight pattern recorded as OA-03 in
`openmaic-provenance.md`: a fixed local action vocabulary selects trusted app-owned
content, with no generated HTML, script or arbitrary action execution. The lesson
content is original to this app; no OpenMAIC source code was copied.
