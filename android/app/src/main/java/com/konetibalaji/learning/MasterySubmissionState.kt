package com.konetibalaji.learning

/** Process-local preconditions. A restart must resume from the server before submitting. */
internal class MasterySubmissionState {
    private val tokens = mutableMapOf<String, String>()

    fun remember(sessionId: String, token: String) {
        require(token.isNotBlank()) { "Missing learning state. Resume the session." }
        tokens[sessionId] = token
    }

    fun expected(sessionId: String): String = requireNotNull(tokens[sessionId]) {
        "Learning state is unavailable. Resume the session before submitting."
    }

    fun clear() = tokens.clear()
}
