package com.konetibalaji.learning

/** Verify server identity before saving a session; roll back every provisional failure. */
fun <T> establishVerifiedSession(verifyProfile: () -> T, persist: (T) -> Unit, rollback: () -> Unit): T {
    try {
        return verifyProfile().also(persist)
    } catch (failure: Exception) {
        try { rollback() } catch (_: Exception) {
            throw ApiFailure(0, false, "Sign-in failed and saved credentials could not be cleared. Please sign in again.")
        }
        throw failure
    }
}
