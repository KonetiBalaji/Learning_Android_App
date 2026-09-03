package com.konetibalaji.learning

fun googleExchangeFailure(status: Int): ApiFailure = ApiFailure(status, false, when (status) {
    401, 422 -> "Google sign-in could not be verified. Please try again."
    409 -> "An account already uses this email. Use its existing sign-in method; accounts are not linked automatically."
    else -> apiFailure(status, authenticationRequest = true).message.orEmpty()
})
