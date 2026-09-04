# Chapter explorer device QA

## Scope

`ChapterExplorerDeviceTest` closes the device-rendering gap for the thirteen
Grade 8 specialized explorers that previously had only JVM model and route
coverage. It uses the production `InteractiveLessonExplorer` dispatcher and
production composables; there is no test-only explorer implementation.

For every route below, the test renders the explorer on the dedicated API 36
AVD, enables Android's Accessibility Test Framework checks, asserts the visible
heading, scrolls to and taps an alternate learner control, and asserts the
resulting selected state:

- Math: Decimals, Percentages, Algebra, Geometry
- Science: Matter, Force and Motion, Ecosystems
- English: Reading Comprehension, Vocabulary, Writing
- Social Studies: History, Civics, Economics

The four earlier explorer workflows remain covered by their end-to-end scripts:
Math Fractions, Science Cells, English Grammar and Social Studies Geography.

## Reproducible command and result

From `android` with the `LearnSmart_API36` AVD connected:

```powershell
.\gradlew.bat :app:connectedDebugAndroidTest
```

Verified on 2026-09-04: 13 tests ran, 0 failures, 0 errors and 0 skipped on
`LearnSmart_API36(AVD) - 16`. The generated XML result is
`app/build/outputs/androidTest-results/connected/debug/TEST-LearnSmart_API36(AVD) - 16-_app-.xml`.

## Evidence boundary

This proves that each production route resolves to a rendered native control and
that its learner-controlled selection changes on an API 36 emulator, with no
error-level finding from the automated Accessibility Test Framework checks
triggered by those actions. Automated checks cannot establish traversal order,
spoken clarity or actual assistive-technology usability. This evidence therefore
does not claim full login-to-mastery navigation coverage, manual TalkBack review,
physical-device coverage, curriculum-board approval or user acceptance. Those
gates remain separately tracked in
`release-acceptance.md`.
