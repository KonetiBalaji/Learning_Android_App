# Google sign-in backend exchange

Status: backend implementation only. Android Credential Manager integration,
Google OAuth client setup, a real sign-in, device recovery and UAT remain open.
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
limits, audit policy, client nonce/flow handling, actual Android exchange and user
acceptance. No browser cookie login route or access to Google APIs is introduced;
Google refresh/access tokens are not stored. Incoming ID tokens remain bearer
credentials until their expiry; this is not a one-use authorization-code protocol.

Design reference: [Google's backend authentication guidance](https://developers.google.com/identity/sign-in/web/backend-auth)
recommends verifying ID tokens server-side and using `sub` as identity rather than
email; it also explains the limits of third-party email ownership claims.
