# Continuous integration quality gate

`.github/workflows/quality.yml` runs for pull requests and pushes to `main` or
`agent/mvp-implementation`. It uses read-only repository permissions and cancels
superseded runs for the same ref.

Three independent jobs prevent one toolchain failure from hiding another:

- repository hygiene rejects tracked `artifacts/` content and known API-key,
  Google-key and private-key shapes;
- backend installs the committed `uv.lock` with Python 3.12 and runs the complete
  pytest suite without an OpenAI key;
- Android installs Java 21 plus API/build-tools 37, then runs debug JVM tests,
  lint and APK assembly. Its debug APK and reports are retained for seven days.

The uploaded debug APK is test evidence only. It is not the signed private release
APK, does not contain an OpenAI key and cannot satisfy UAT or production gates.
Live provider evaluations and emulator/physical-device journeys are intentionally
separate because they require protected credentials or dedicated devices.

The first branch run proved backend and hygiene on GitHub, but Android failed with
exit 126 because the Gradle wrapper lacked its executable Git mode. It also exposed
Node 20 deprecation warnings in older action tags. The wrapper mode and official
checkout/setup/upload action generations were updated; this failed run is retained
as diagnostic evidence, not counted as a green quality gate.
The next run confirmed those updates but showed that the hosted runner does not
place `sdkmanager` on `PATH`; the workflow now invokes the executable explicitly
under the runner-provided `ANDROID_HOME` instead of adding another deprecated
setup action. That run is likewise failure evidence, not acceptance.

GitHub Actions run `33871289020` at commit
`64f12b1b43d7fd9e279ddb214bfdb278e8a29f52` is the first accepted remote gate.
On 2026-09-04, repository hygiene passed in 6 seconds, the complete backend job
passed in 1 minute 35 seconds, and the clean Android job passed in 7 minutes
33 seconds. The Android job completed JVM tests, lint and debug APK assembly,
then uploaded the non-expired `android-debug-verification` artifact (20,042,063
bytes) with seven-day retention. The authoritative run is
<https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/33871289020>.

Local YAML parsing and the same backend/Android commands verify the workflow's
structure and commands before commit. Run `33871289020` additionally proves the
hosted-runner SDK setup, clean-checkout commands and artifact publication. It does
not replace the separate emulator, physical-device, live-provider or UAT gates.

Pre-push local verification parsed all three YAML jobs, confirmed the installed
SDK package name is `platforms;android-37.0`, completed the locked dependency audit,
passed **515 backend tests with one Windows symlink-privilege skip**, and passed
**141 Android JVM tests**, lint and debug APK assembly. These numbers are local
evidence; the remote run is recorded separately only after GitHub reports it.
