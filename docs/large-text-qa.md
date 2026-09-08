# Large-text layout work

Text-bearing primary/outlined buttons and the rewrite field now use minimum
heights rather than fixed heights, allowing wrapped text to expand. Grade and
subject cards do the same. Their small grids share the outer page scroll instead
of fixed-height nested scrolling viewports. Column counts respond to available
width and font scale, with caps of three grades or two subjects per row.

Two JVM tests check column-count behavior and invalid dimensions. Android debug
build, lint and all 97 JVM tests passed. This is not a complete accessibility audit.

## API 36 check, 2026-09-03

`scripts/qa-large-text.ps1` requires the dedicated LearnSmart_API36 emulator and
an existing synthetic QA account at completed document results, study home or
subjects. It installs the debug APK without clearing account data, sets the system
font scale to 2.0, navigates through subjects/settings/Grade 8, captures screenshots
and restores the previous scale in a finally block, checking restoration.

The final run exited zero. Visual inspection showed readable single-column subject
cards, an unclipped two-line parent-progress button and readable grade cards.
Grade 8 was selected and returned to subjects. All three screenshots were inspected.
The setting was restored. The first two runs stopped on incorrect script navigation
assumptions (upload-home vs subjects after restart); both restored the scale.
The script now accepts those valid starting screens. No live AI requests occurred.

The test checks button visibility, not parent-role authorization. It does not prove
every grade, subject, screen, theme, error dialog, speech control or rewrite field
works at large text. TalkBack, keyboard/switch navigation, touch-target and contrast
audits, physical-device/small-screen/landscape coverage and actual UAT remain open.
Screenshots at scroll boundaries may show partially off-screen cards; inspected
fully visible cards did not clip their text inside the card. Layout fixes do not
complete curriculum coverage or parent/teacher access requirements.

## Physical-device check, 2026-09-08

Signed candidate `0.3.0-uat.19` was exercised on the 1080x2400 Xiaomi Android 13
device at system font scale 1.3. The Grade 8 subject dashboard reflowed from two
columns to a readable single column; headings, progress labels and cards remained
inside their containers and the page remained scrollable. The Settings screen was
then visually inspected in both dark and light app themes at the same scale. Its
navigation, theme control, grade/interests controls and retention card remained
readable without horizontal clipping. The original dark preference and font scale
1.0 were restored and the app relaunched successfully.

This is physical-device visual and hierarchy evidence for two representative
screens, not a complete contrast measurement, landscape test, TalkBack spoken
traversal or human usability acceptance. UX-01 therefore remains partial.
