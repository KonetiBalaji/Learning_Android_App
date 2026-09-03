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

References: [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
and [backup controls](https://developer.android.com/identity/data/autobackup).
