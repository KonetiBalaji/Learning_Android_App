package com.konetibalaji.learning

internal fun validateGoogleChallenge(nonce: String, expiresInSeconds: Int): String {
    require(nonce.length in 43..128 && nonce.all { it.isLetterOrDigit() || it == '_' || it == '-' })
    require(expiresInSeconds in 1..300)
    return nonce
}

fun googleExchangeFailure(status: Int): ApiFailure = ApiFailure(status, false, when (status) {
    401, 422 -> "Google sign-in could not be verified. Please try again."
    409 -> "An account already uses this email. Use its existing sign-in method; accounts are not linked automatically."
    else -> apiFailure(status, authenticationRequest = true).message.orEmpty()
})
