# Learnly Android client

The Android client is a Compose implementation of the core MVP flow:

1. Create a local development account.
2. Pick a PDF, DOCX, or TXT study file.
3. Review detected chapters and choose one.
4. Generate a ten-question, source-grounded session.
5. Answer one question at a time and read immediate teaching feedback.
6. Review the completed-session score and missed questions.

## Local build

The app expects the backend at `http://10.0.2.2:8000` when running in an Android emulator. Start it first from `../backend`.

Install Android SDK Platform 37.0, Build Tools 37.0.0, and accept the Android SDK license in your local SDK Manager. Then run:

```powershell
cd android
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat :app:assembleDebug
```

The resulting debug APK is placed under `app/build/outputs/apk/debug/`.

## Development-only transport

The manifest enables cleartext traffic only so the emulator can reach a locally running API. Production builds must use HTTPS and should remove `android:usesCleartextTraffic="true"`.
