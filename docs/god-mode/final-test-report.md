# Saras dev verification report

Runtime revision: `793bd2600bf8c5c95f4e10a66644c24139c21354` (base `0181f83`). The audit pack follows in a documentation-only commit. The app targets API 36; the connected device runs Android 15 (API 35).

| Check | Actual result | Evidence |
|---|---|---|
| Backend pytest | 102 passed; one Starlette/httpx deprecation warning | `.venv\Scripts\python.exe -m pytest backend/tests -q`; includes three new lifecycle cases |
| Android JVM | 4 passed; 0 failed or skipped | Gradle XML: OfflinePracticeTest and QuizRulesTest |
| Android emulator | 7 passed; 0 failed or skipped | Connected suite on SarasTest, Android 15; four UI flows and three cache tests. Verified scan citation return to the same quiz, account deletion clearing a saved copy, airplane mode, sync and remote deletion. |
| Android debug build | Passed | Debug APK and instrumentation APK assembled |
| Android debug lint | Passed; 0 errors, 14 warnings | lint-results-debug.txt |
| Docker HTTPS staging | Passed on disposable Linux Compose | [GitHub Actions run 41950761292](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/41950761292): redirect, trusted TLS, readiness, upload, real OCR and confirmation, semantic retrieval, owner isolation, quiz and web account deletion |
| Separately reported Python unittest core | REPORTED ONLY: 51 | No attributable revision or test files; excluded from the totals. See [reconciliation](reconciliation.md). |

Android command: `scripts/build-android.ps1 -ConnectedTests`. The build finished successfully. The emulator uses disposable backend fixtures; the Docker smoke independently verifies a Linux deployment.

**NOT VERIFIED:** live AI and grounding, real difficulty accuracy, original logo integration, public production TLS and smoke, authorized Play signing, final store declarations and publishing. Prior disposable signing and offline process restart evidence is historical, as recorded in the release and offline guides. See [external blockers](external-blockers.md).
