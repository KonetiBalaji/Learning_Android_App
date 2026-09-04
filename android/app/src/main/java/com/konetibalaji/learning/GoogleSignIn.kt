package com.konetibalaji.learning

import android.app.Activity
import android.content.Context
import android.content.MutableContextWrapper
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.CancellationException

/** Only the ID token crosses to the backend; profile claims are never local identity. */
suspend fun requestGoogleIdToken(activity: Activity, nonce: String): String {
    check(BuildConfig.GOOGLE_SERVER_CLIENT_ID.isNotEmpty())
    validateGoogleChallenge(nonce, 300)
    try {
        val option = GetSignInWithGoogleOption.Builder(BuildConfig.GOOGLE_SERVER_CLIENT_ID)
            .setNonce(nonce).build()
        val result = CredentialManager.create(activity).getCredential(
            context = MutableContextWrapper(activity),
            request = GetCredentialRequest.Builder().addCredentialOption(option).build(),
        ).credential
        require(result is CustomCredential && result.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL)
        return GoogleIdTokenCredential.createFrom(result.data).idToken.also { require(it.length in 1..16384) }
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: GetCredentialCancellationException) {
        throw ApiFailure(0, false, "Google sign-in was cancelled. You are still signed out.")
    } catch (_: NoCredentialException) {
        throw ApiFailure(0, false, "No Google account is available. Add an account on this device or use email sign-in.")
    } catch (_: GetCredentialException) {
        throw ApiFailure(0, false, "Google sign-in is unavailable. Try again or use email sign-in.")
    } catch (_: Exception) {
        throw ApiFailure(0, false, "Google sign-in could not be verified. Please try again.")
    }
}

/** Provider cleanup must not prevent local logout, and is not permission revocation. */
suspend fun clearGoogleCredentialState(context: Context): String? {
    if (BuildConfig.GOOGLE_SERVER_CLIENT_ID.isEmpty()) return null
    return try {
        CredentialManager.create(context).clearCredentialState(ClearCredentialStateRequest())
        null
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        "You are signed out locally, but the Google account chooser could not be reset. Google permissions have not been revoked."
    }
}
