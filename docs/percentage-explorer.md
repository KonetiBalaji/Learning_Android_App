# Percentage equivalence explorer

The Grade 8 Mathematics `percentages` tutor route includes a native 10 by 10 grid.
The learner can select 25%, 50% or 75%; exactly that many of the 100 cells are
highlighted and the matching decimal and simplified fraction are shown. The grid's
accessibility description reports both the highlighted count and percentage.
Exploration cannot submit an assessment response or change mastery.

JVM tests verify the route and the exact percentage, decimal and fraction mappings.
Android JVM tests, lint and debug assembly pass. This is not rendered-device,
TalkBack, broader percentage curriculum, physical-device or UAT evidence.

Like the other bounded native explorers, this follows OA-03 in
`openmaic-provenance.md`: fixed app-owned actions select trusted app-owned content.
No generated HTML, script or arbitrary action is executed, and no OpenMAIC source
code was copied.
