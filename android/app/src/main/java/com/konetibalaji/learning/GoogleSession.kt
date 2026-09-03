package com.konetibalaji.learning

fun googleExchangeFailure(status: Int): ApiFailure = ApiFailure(status, false, when (status) {
    401, 422 -> "Google sign-in could not be verified. Please try again."
    409 -> "An account already uses this email. Use its existing sign-in method; accounts are not linked automatically."
    else -> apiFailure(status, authenticationRequest = true).message.orEmpty()
})

/** Verify server identity before saving a session; roll back every provisional failure. */
fun <T> establishGoogleSession(verifyProfile: () -> T, persist: (T) -> Unit, rollback: () -> Unit): T {
    try {
        return verifyProfile().also(persist)
    } catch (failure: Exception) {
        try { rollback() } catch (_: Exception) {
            throw ApiFailure(0, false, "Sign-in failed and saved credentials could not be cleared. Please sign in again.")
        }
        throw failure
    }
}
