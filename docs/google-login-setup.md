# Google Login release setup

Google Login is implemented but remains disabled unless one Google Cloud OAuth Web
client ID is configured identically in the backend and Android release. The Web
client ID is public configuration; never use or embed its client secret.

## Google Cloud configuration

1. Configure the OAuth consent screen for the owned Google Cloud project. During
   UAT, keep the app in testing and add the intended tester Google accounts.
2. Create an Android OAuth client with package name
   `com.konetibalaji.learning` and the owned release certificate SHA-1:
   `3E:8D:71:B1:4B:98:7A:49:91:A0:77:FD:9B:66:A9:EF:06:98:6B:EF`.
3. Create a Web application OAuth client. Copy its client ID ending in
   `.apps.googleusercontent.com`; do not copy its client secret into this project.
4. Set that Web client ID as the protected backend configuration value
   `LEARNING_GOOGLE_CLIENT_ID`.
5. Restart the backend and verify `GET /v1/auth/google/challenge` returns 200 for
   an authenticated-independent sign-in start rather than the disabled 503.

## Build the configured private APK

Build the next monotonically versioned candidate with the same Web client ID:

```powershell
.\scripts\build-private-apk.ps1 `
  -BackendUrl 'https://the-owned-backend.example.org' `
  -VersionCode 5 `
  -VersionName '0.3.0-uat.3' `
  -GoogleServerClientId '123456789-example.apps.googleusercontent.com'
```

The builder validates that the value has Google OAuth client-ID syntax and passes
it only as the public Android build configuration. The APK hash in the candidate
manifest binds the resulting configuration to UAT.

## Acceptance

On the signed physical-device candidate, verify successful account selection,
new Google-only account creation, sign-out/sign-in recovery, cancellation, replayed
or expired nonce rejection, and the documented collision behavior for an existing
password account. Record evidence against AUTH-02 in the candidate-bound UAT file.
Do not mark AUTH-02 passed based only on mocked backend tests or the disabled-button
device check.
