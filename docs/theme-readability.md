# Theme readability

The previous device captures showed white status icons on the light background.
The app now enables edge-to-edge consistently and sets status/navigation icon
appearance from its saved app theme, not just the device theme. This follows the
[Android system-bar guidance](https://developer.android.com/develop/ui/compose/system/setup-e2e).

Headings, buttons, success/error accents and secondary text now use the current
Material color scheme. Previously fixed pale sign-in, tutor, mastery and tip-card
backgrounds now adapt to dark mode. Practice success and tip cards use paired
container/content colors. Error dialogs now render inside the app's theme.
The light success accent was darkened for readable text.

Progress indicators now use the active theme's `surfaceVariant` track instead of
a fixed pale track. Automated checks require at least 3:1 contrast between the
primary/success indicators and their track in both light and dark themes, as well
as between primary interactive outlines and the surface.

Verification on 2026-09-03:

- Android build/lint and 32 JVM tests passed. Two new tests require at least 4.5:1
  luminance contrast for the selected text/surface, button, container and accent
  pairs in both themes. This is not a full accessibility audit.
- `scripts/qa-theme.ps1` passed after the document recovery QA fixture. It toggles
  the actual settings control, restarts the app, verifies the persisted switch
  state, and returns the disposable account to light mode.
- Light settings and restarted dark settings screenshots were visually inspected:
  readable foregrounds and visible dark/light status icons, respectively.
  Captures are under `artifacts/qa-theme-*.png` (not committed).
- Initial lint activity-context casting was corrected to LocalActivity. The first
  QA selector assumed a native Switch; inspection showed a checkable Compose View,
  and the corrected selector passed on rerun.

Still required: every learning screen in both themes, dialog visuals, large fonts,
TalkBack labels/focus, physical devices, older API levels and human usability review.
These checks do not constitute user UAT or production acceptance.
