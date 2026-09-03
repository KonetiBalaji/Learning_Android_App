# Google sign-in exchange and Android integration

Status: backend and Android integration implemented. Google OAuth client setup,
a real sign-in, configured-device recovery and UAT remain open.
AUTH-02 is partial, not delivered Google login.

`POST /v1/auth/google` accepts JSON containing only `id_token` (1–16,384 characters)
and returns the existing local bearer-token contract. `LEARNING_GOOGLE_CLIENT_ID`
must name the approved web/server OAuth client audience; absence disables the
exchange with 503. No client ID or credentials have been configured by this work.

The Google-auth library verifies signature, expiration/issued-at and audience,
and validates Google's issuer. Additional checks require exact audience/issuer,
a bounded nonempty subject, a valid email and boolean `email_verified=true`.
Certificate fetches use a five-second timeout and a per-call closed session.
Invalid credentials return generic 401; certificate transport failures return
generic 503. Exceptions, ID tokens and Google profile fields are not logged by
the exchange. Standard request-schema validation behavior remains unchanged.
Android must continue suppressing raw validation bodies, including auth requests.

The additive `google_accounts` table maps unique Google subjects to local users,
with a unique user foreign key and deletion cascade. Identity creation is serialized
inside the same database transaction as user creation. Repeat sign-in uses the
subject even if Google reports a different email. Stored email is not silently
changed. The Google-only password sentinel cannot pass local password verification.
Deleting the local account removes its mapping and invalidates old local sessions
through the existing owner-existence check. Signing in again may create a new,
empty account; it cannot restore deleted learning data.

There is no automatic account linking: a previously unseen subject whose email
matches any existing account returns 409. A matching email is never evidence for
accessing a password account. Google-hosted and third-party email claims are not
used as parent/teacher consent, recovery authorization or permission to send
sensitive data. In particular, Google's verified flag alone does not prove current
ownership of a third-party mailbox. Any future email-based recovery, linking or
contact verification needs its own proof and policy before implementation.

## Verification and release work

Android uses Credential Manager 1.6.0 and Google ID 1.2.0 with the explicit
`GetSignInWithGoogleOption` account chooser. Set the public web/server audience
using `-PgoogleServerClientId=<approved-web-client-id>` and configure the same
audience in the backend. This is separate from the OpenAI API key and is not an
OAuth secret. Invalid nonempty client ID syntax fails Gradle configuration;
omitting it builds a disabled button with an explanation. No client ID was invented.
The approved Android package/signing certificate must also be registered with Google.

One ViewModel operation covers the chooser, backend exchange and secure save;
email inputs, mode switching and both sign-in buttons are disabled meanwhile.
The Google ID token is sent only to the backend and is not persisted. The app
fetches `/v1/account` with the provisional local token, uses the server-stored
email for account-scoped resume pointers (not Google's possibly changed email),
and only then persists the existing encrypted local session. Exchange/profile/save
failures clear provisional credentials. Account collisions explicitly direct the
learner to the existing sign-in method without merging accounts. Raw provider
exceptions and backend response bodies are never shown. Cancellation is recoverable.
Local sign-out/deletion attempts provider credential-state cleanup when configured;
a cleanup failure does not undo local logout and is reported. This does not revoke
Google permissions or delete the Google account. No nonce protocol is claimed.

On 2026-09-03 Android assembleDebug, lintDebug and **103 JVM tests** passed,
including six new server-identity/persistence rollback and safe-error tests.
`scripts/qa-google-disabled.ps1` installed the default APK on LearnSmart_API36,
signed out the synthetic QA account without clearing app data and verified that
the Google button was disabled with explanatory copy. Its screenshot
`artifacts/qa-google-disabled.png` was visually inspected: labels were readable
and unclipped. A transient null UI-automation root was recovered by the bounded
fresh-dump retry. This is not configured Google login, lifecycle recovery or UAT.
Account chooser cancellation, rotation/backgrounding, real exchange, Google
logout cleanup and Google-account deletion still require configured-device QA.
The six helper tests do not exercise actual HTTP, Keystore or Credential Manager.

Tests replace only Google's certificate-fetch boundary with a locally generated
RSA public key; ID tokens use real RSA signatures and pass through Google's
verification implementation. Cases cover invalid signature, wrong audience/issuer,
expired/future-issued tokens, malformed subject/email, unverified email, disabled
configuration, transport failure, repeat identity, changed email, collision denial,
password denial and account-deletion cascade/session invalidation. These synthetic
tests are not evidence of a live Google account or configured OAuth consent screen.

On 2026-09-03 the full backend suite passed **266 tests, 1 existing Windows
symlink-privilege test skipped**, including 12 new exchange tests, with the existing
Starlette/httpx warning. The initial test used an incorrect deletion URL, and the
first full run exposed a nested-router compatibility issue in existing route checks;
both were corrected before the successful rerun. No existing security assertion
was removed and no live Google or OpenAI token exchange was performed.

Production still requires approved OAuth audiences/package/signing configuration,
HTTPS, certificate-cache/rotation and outage verification, authentication rate
limits, audit policy, client nonce/flow review, actual Android exchange and user
acceptance. No browser cookie login route or access to Google APIs is introduced;
Google refresh/access tokens are not stored. Incoming ID tokens remain bearer
credentials until their expiry; this is not a one-use authorization-code protocol.

Design reference: [Google's backend authentication guidance](https://developers.google.com/identity/sign-in/web/backend-auth)
recommends verifying ID tokens server-side and using `sub` as identity rather than
email; it also explains the limits of third-party email ownership claims.

Android references: [Credential Manager Google sign-in](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation),
[stable Credential Manager releases](https://developer.android.com/jetpack/androidx/releases/credentials),
and [Google ID releases](https://developers.google.com/identity/android-credential-manager/releases).
The enabled button's final Google branding review remains a release gate.

## Shared password-session correction

The subsequent authentication audit found that password registration/login still
persisted a token before verifying the server profile and used the typed email
locally. Both password paths now share `establishVerifiedSession` and
`finishAuthentication` with Google: fetch the profile using a provisional token,
commit the server-stored email, then save the encrypted session. Any exchange,
profile or persistence failure clears provisional credentials; password error
messages retain their existing safe wording. Existing account-scoped learning
resume pointers are preserved. A successful server registration cannot be rolled
back by the client if the later profile fetch fails: the user must sign in to that
newly created account, not retry creating it indefinitely.

On 2026-09-03 Android build/lint and 104 JVM tests passed. The shared helper tests
cover ordered verification/persistence, profile and storage failures, cancellation,
rollback failure and preservation of the safe password-rejection error.
`scripts/qa-auth-profile.ps1` passed against the isolated QA service and API 36
emulator: mixed-case email registration, server-normalized identity display,
sign-out, wrong-password rejection, successful retry and persisted-session restart.
It starts signed out, creates only a synthetic account, and does not clear app data.
The resulting `artifacts/qa-auth-profile.png` was visually inspected: the long
synthetic email wraps without clipping and settings controls remain readable.
A transient null automation root recovered through the bounded fresh-dump retry.
Device-level profile-fetch outage and Keystore-write failure injection remain open;
helper unit tests are not evidence for those device paths or for real Google login.
