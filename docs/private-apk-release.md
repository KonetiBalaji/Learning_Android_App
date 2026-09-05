# Private APK release contract

Status: release packaging is implemented and QA verified. A dedicated private-release
identity now exists outside Git on the development machine. No production backend,
UAT candidate or private distribution is claimed.

## Required operator inputs

Release signing material never belongs in Git, Gradle properties, the APK source
tree or command-line arguments. By default, the build script can load the local
`%USERPROFILE%\.learnsmart\release\signing-profile.clixml` profile. Its passwords
are protected with Windows DPAPI for the current Windows user, and the containing
directory has a restricted ACL. A different profile can be supplied with
`-SigningProfile`.

For a CI or another operator environment, set these environment variables in its
secret-bearing session instead:

- `LEARN_SMART_RELEASE_STORE_FILE`: absolute path to the owned PKCS12/JKS file
- `LEARN_SMART_RELEASE_STORE_PASSWORD`
- `LEARN_SMART_RELEASE_KEY_ALIAS`
- `LEARN_SMART_RELEASE_KEY_PASSWORD`

Then run `scripts/build-private-apk.ps1 -BackendUrl
https://the-confirmed-backend.example -VersionCode 2 -VersionName 0.2.0-uat.1`.
The HTTPS URL is public configuration,
not a secret. It must be the verified production or approved UAT service, never
localhost, an emulator alias or a placeholder domain.

The version code must be a positive Android integer and must increase beyond any
candidate manifest already in the selected output directory. The version name must
use a bounded semantic form. This makes private APK upgrades and manifests
unambiguous across commits. The build fails closed when version identity, the HTTPS
endpoint or any signing input is missing, the keystore is absent, or tracked files
differ from HEAD. Gradle signs the release
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

Independently verify the exact artifact and deployed service before installing it:

```powershell
cd backend
uv run python -m app.release_candidate ..\artifacts\private-release\candidate-manifest.json --expected-environment staging
```

Use `production` only for the final production deployment. The verifier rejects a
modified or missing APK, malformed manifest, local or placeholder backend,
non-HTTPS origin, unhealthy service, wrong environment or revision, and a
production service that does not report the reviewed OpenAI provider and model.
It also rejects a backend whose `/ready` probe cannot prove required database
schema/integrity/write admission and writable upload storage for the same revision.
Its successful JSON output contains hashes and deployment identity but no secrets.
It does not prove backup restoration, sustained capacity, or model quality; install
the APK; or grant UAT or production acceptance.

The signing keystore and its recoverable credentials must be durably backed up by
the user before distribution. Losing either prevents trusted upgrades; replacing
the key creates a different Android signing identity. The DPAPI profile is bound to
this Windows identity and is not, by itself, a portable recovery backup.

## Verification

On 2026-09-04, missing signing variables caused `validateReleaseSigning` to fail
with the four missing names. A disposable two-day RSA QA certificate then produced
a release APK against `https://qa.invalid`; `assembleRelease` and lint-vital passed,
and `apksigner` verified APK Signature Scheme v2 with one signer. This proves the
build/sign/inspect mechanism, not endpoint reachability, certificate ownership,
install/upgrade behavior, UAT or production readiness.

Later on 2026-09-04, the project release identity was generated as a 3072-bit RSA
PKCS12 key with a 25-year validity and stored outside the repository. Its certificate
SHA-256 is
`147c2f52160ccb5f0a6d99d5908dfe3775df5477102ab6e0cc2bf1f215040f0d`.
The build profile contains only DPAPI-protected credentials; neither credentials nor
private-key bytes are committed.

On 2026-09-04, commit `0c30e05` produced an owned-key QA release with explicit
`versionCode=2` and `versionName=0.2.0-qa.1`; signature, package metadata and the
manifest matched. API 36 first installed the same-key `versionCode=1` artifact from
commit `3154cd4`, then `adb install -r` upgraded it successfully to version 2 while
preserving the package UID and signing key set. The endpoint was deliberately
`https://qa.invalid`, so this proves signed private-APK upgrade compatibility only,
not backend reachability, a UAT candidate or production deployment.

Before UAT, rerun with an approved reachable HTTPS staging backend and the owned
release key, install the exact hashed APK on the agreed physical device, and attach
its manifest to the UAT record. Before production, repeat against the production
backend and complete the operational checks in `docs/uat-runbook.md` and
`docs/release-acceptance.md`.
