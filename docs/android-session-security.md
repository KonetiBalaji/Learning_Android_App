# Android session and transport protection

The bearer token is stored as an authenticated AES-256-GCM envelope in private
preferences. The encryption key is generated and retained by AndroidKeyStore;
no key bytes or plaintext fallback are stored by the app. Each encryption uses
a fresh provider-generated nonce and version-specific associated data.

Startup performs key and preference work on the IO dispatcher. Existing legacy
`token` preferences migrate with an atomic checked commit that writes ciphertext
and removes plaintext. Corrupt envelopes, unavailable keys and failed migrations
clear saved authentication and require a fresh login. Login only accepts a token
in memory after persistence succeeds. Logout and account deletion clear both
token fields. This protects the token, not all profile/learning preferences, and
does not make a compromised running device trustworthy.

Backups are disabled. Explicit cloud-backup and device-transfer exclusions cover
app files, databases, shared preferences and external app files. Production network
configuration rejects cleartext traffic; the debug overlay allows only the named
emulator/loopback hosts. A release build requires an explicit HTTPS
`-PreleaseApiBaseUrl` and rejects missing/local endpoints. This is configuration
validation, not proof of host ownership, server security, reachability or deployment.
Release signing and a confirmed production backend remain pending.

Release packaging now requires an explicit owned keystore through environment-only
inputs, verifies the resulting APK signature and emits a commit/hash/certificate
manifest. The successful QA path used only a disposable certificate and placeholder
HTTPS endpoint, so final signing ownership and production deployment remain pending.
See `private-apk-release.md`.

## Verification on 2026-09-03

- `:app:assembleDebug :app:testDebugUnitTest :app:lintDebug` passed.
- Eight JVM tests passed: four navigation tests and four cipher tests covering
  round-trip, nonce uniqueness, wrong keys, tampering and invalid envelopes.
- Dedicated API 36 emulator: authenticated tutor recovery after forced process
  death, rubric feedback recovery and remaining assessment before mastery passed
  against the scripted QA backend. Read-only preferences inspection confirmed
  encrypted envelope present and legacy plaintext token absent, without printing
  secret values. The QA script now includes this storage assertion.
- `:app:validateReleaseEndpoint` failed as expected without a property and with
  `http://example.com`. A placeholder `https://qa.invalid` passed syntactic
  validation only; it is not configured or claimed as a deployed backend.
- Legacy migration, Android key invalidation and OEM backup/transfer behavior
  still require dedicated device-level failure tests. JVM cipher tests do not
  test AndroidKeyStore itself. Dependency metadata access returned HTTP 502;
  no unverified instrumentation dependency was added.

## Authenticated-decryption device evidence (2026-09-04)

`scripts/qa-corrupt-session.ps1 -ResetTestAppData` passed on the dedicated API 36
emulator. After Android persisted a real encrypted bearer-token envelope, the QA
runner force-stopped the app and replaced only that isolated preference value with
a malformed versioned envelope. Startup rejected authenticated decryption, removed
encrypted and legacy credential fields, displayed the safe sign-in recovery message,
and remained signed out after another restart. Password reauthentication succeeded
before the disposable account was deleted. No token, ciphertext or password was
printed. This verifies the app's altered-ciphertext path on AndroidKeyStore, not OEM
key invalidation, hardware-backed storage certification, physical-device behavior
or user UAT. Final Android verification passed 126 JVM tests, lint and debug APK
assembly.

References: [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
and [backup controls](https://developer.android.com/identity/data/autobackup).
