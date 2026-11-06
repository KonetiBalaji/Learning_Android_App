# Google sign-in on Saras

Saras uses Android Credential Manager to request a Google ID token. The backend verifies the token and a five-minute, one-use challenge before creating a normal Saras session. Google accounts are keyed by the verified Google subject. Signing in with Google creates a separate account from any existing username/password account. Saras does not merge account data based on an email address.

In the Saras Google Cloud project:

1. Configure the OAuth consent screen. Add the Google account used for device testing if the app is in Testing.
2. Create a Web application OAuth client. Set its public client ID as `STUDY_GOOGLE_CLIENT_ID` in the backend environment. A client secret is unnecessary for this flow.
3. Create an Android OAuth client in the same project for package `com.studycompanion` and the SHA-1 of the certificate that actually signs the test APK. For a Play build, register the Play app signing certificate fingerprint.
4. Restart the backend and use its HTTPS address in the Android app. The debug APK also supports loopback through ADB for a local test.

Check the Google account chooser, consent, first sign-in, sign-out, a second Google account, and returning to the first account. Use only disposable study data. Verify each account sees only its own library. Google sign-in is disabled on a backend without the client ID. Username and password sign-in remains available.

Google accounts can delete their account and associated data in Saras Settings. The standalone password-based deletion page currently serves password accounts. Provide and verify a Google-capable web deletion option before a public Play release that enables Google sign-in.

Automated backend tests verify signed test tokens using a local test certificate, rejection of invalid claims and replay, account isolation, session revocation, and deletion. Live sign-in against a Saras OAuth client requires the configured Google Cloud project and a consented test account.

[Android Credential Manager guide](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation) · [Google backend token verification](https://developers.google.com/identity/sign-in/android/backend-auth)

## Live device verification

On the Android 13 test phone, the debug APK used the dedicated Saras Learning Google Cloud project in Testing mode and a local backend reached through ADB forwarding. The first Google sign-in opened the Library and created one Google account and one Saras session. Signing out returned the phone to the login screen and removed the server session. Signing in again with the same Google account reopened the Library, kept the Google account count at one, and created a new session. The test used one approved Google account. Public access and the Play signing certificate remain separate release checks.
