# Geometry triangle-area explorer

The Grade 8 Mathematics `geometry` tutor route includes a native triangle-area
explorer. Learners select one of three positive base/perpendicular-height pairs. The
diagram marks the perpendicular height and shows `base × height ÷ 2` with the exact
whole-number area. Its accessibility description states the selected dimensions and
area. Exploration cannot submit an assessment response or change mastery.

JVM tests verify the three exact areas and reject non-positive dimensions or examples
that would silently truncate a non-integral result. API 36 component and full locked-
chapter tutor journeys render the explorer, select base 8 and height 5, and verify
unchanged mastery; the capture was visually inspected. Manual TalkBack, broader
geometry curriculum, physical-device and UAT evidence remain open.

This follows OA-03 in `openmaic-provenance.md`: fixed app-owned actions select trusted
models. No generated action, HTML, script or OpenMAIC source code is executed or
copied.
