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

Local YAML parsing and the same backend/Android commands verify the workflow's
structure and commands before commit. A local pass cannot prove GitHub runner SDK
availability or a remote green check; the first pushed workflow run must be
inspected before QA-01 can cite remote CI evidence.

Pre-push local verification parsed all three YAML jobs, confirmed the installed
SDK package name is `platforms;android-37.0`, completed the locked dependency audit,
passed **515 backend tests with one Windows symlink-privilege skip**, and passed
**141 Android JVM tests**, lint and debug APK assembly. These numbers are local
evidence; the remote run is recorded separately only after GitHub reports it.
