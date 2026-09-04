# Private APK release contract

Status: release packaging implemented and QA verified with a disposable local
certificate. No production backend, owned signing key, UAT candidate or private
distribution is claimed.

## Required operator inputs

Release signing material never belongs in Git, Gradle properties, the APK source
tree or command-line arguments. Set these environment variables in the operator's
secret-bearing session:

- `LEARN_SMART_RELEASE_STORE_FILE`: absolute path to the owned PKCS12/JKS file
- `LEARN_SMART_RELEASE_STORE_PASSWORD`
- `LEARN_SMART_RELEASE_KEY_ALIAS`
- `LEARN_SMART_RELEASE_KEY_PASSWORD`

Then run `scripts/build-private-apk.ps1 -BackendUrl
https://the-confirmed-backend.example`. The HTTPS URL is public configuration,
not a secret. It must be the verified production or approved UAT service, never
localhost, an emulator alias or a placeholder domain.

The build fails closed when the HTTPS endpoint or any signing input is missing,
the keystore is absent, or tracked files differ from HEAD. Gradle signs the release
variant only from those environment values and disables cleartext traffic.

## Outputs and identity

The script writes ignored artifacts under `artifacts/private-release`:

- `learn-smart-private-release.apk`
- `candidate-manifest.json`

It verifies the APK signature with Android `apksigner`, reads package/version
metadata from the built APK, and records the immutable Git commit, backend URL,
APK SHA-256, signing-certificate SHA-256 and UTC build time. The manifest explicitly
sets `uat_accepted` and `production_verified` false; those states require separate
human acceptance and deployed-service checks. Passwords, private-key bytes and the
OpenAI key are never written to the manifest.

The final signing keystore must be owned and durably backed up by the user. Losing
it prevents trusted upgrades; replacing it creates a different Android signing
identity. The disposable QA certificate used to verify this pipeline must never be
used for distribution.

## Verification

On 2026-09-04, missing signing variables caused `validateReleaseSigning` to fail
with the four missing names. A disposable two-day RSA QA certificate then produced
a release APK against `https://qa.invalid`; `assembleRelease` and lint-vital passed,
and `apksigner` verified APK Signature Scheme v2 with one signer. This proves the
build/sign/inspect mechanism, not endpoint reachability, certificate ownership,
install/upgrade behavior, UAT or production readiness.

Before UAT, rerun with an approved reachable HTTPS staging backend and the owned
release key, install the exact hashed APK on the agreed physical device, and attach
its manifest to the UAT record. Before production, repeat against the production
backend and complete the operational checks in `docs/uat-runbook.md` and
`docs/release-acceptance.md`.
