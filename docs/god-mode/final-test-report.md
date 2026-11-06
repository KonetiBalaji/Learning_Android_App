# Saras dev verification report

Runtime revision: `ad03dda15c3fdc3bd426491c4416a7b75b30651f` (base `0181f83`). The audit pack follows in a documentation-only commit. The app targets API 36; the connected device runs Android 15 (API 35).

| Check | Actual result | Evidence |
|---|---|---|
| Backend pytest | 102 passed; one Starlette/httpx deprecation warning | `.venv\Scripts\python.exe -m pytest backend/tests -q`; includes owner and lifecycle cases |
| Android JVM | 4 passed; 0 failed or skipped | Gradle XML: OfflinePracticeTest and QuizRulesTest |
| Android emulator | 9 passed; 0 failed or skipped | Connected suite on SarasTest, Android 15; six learning flow tests and three cache tests. Regression checks cover upload retry after a failed library refresh, automatic dismissal of an expired offline result and source dialog, and immediate quiz resume from Library. Existing checks cover OCR citation return, account deletion, airplane mode, sync and remote deletion. |
| Android debug build | Passed | Debug APK and instrumentation APK assembled |
| Android debug lint | Passed; 0 errors, 14 warnings | lint-results-debug.txt |
| Docker HTTPS staging | Passed on disposable Linux Compose | [GitHub Actions run 42026775931](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42026775931): redirect, trusted TLS, readiness, upload, real OCR and confirmation, semantic retrieval, owner isolation, quiz and web account deletion |
| Separately reported Python unittest core | REPORTED ONLY: 51 | No attributable revision or test files; excluded from the totals. See [reconciliation](reconciliation.md). |

Android command: `scripts/build-android.ps1 -ConnectedTests`. The build finished successfully. The emulator uses disposable backend fixtures; the Docker smoke independently verifies a Linux deployment.

**NOT VERIFIED:** live AI and grounding, real difficulty accuracy, original logo integration, public production TLS and smoke, authorized Play signing, final store declarations and publishing. Prior disposable signing and offline process restart evidence is historical, as recorded in the release and offline guides. See [external blockers](external-blockers.md).

## Public release verification

| Gate | Status | Evidence still needed |
|---|---|---|
| Approved branding | NOT VERIFIED | Approved assets and inspection of launcher, splash and headers in light and dark modes |
| Live AI | NOT VERIFIED | No live evaluation run. Easy, Medium, Hard and Mixed each have zero evaluated items. Accuracy is unavailable. |
| Public production | NOT VERIFIED | Production URL, trusted public certificate and completed smoke results from the supplied host |
| Authorized Play bundle | NOT VERIFIED | Bundle signed with the authorized upload key, matching certificate fingerprint and final privacy and Data safety declarations |
