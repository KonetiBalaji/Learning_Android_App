package com.konetibalaji.learning

/** Generation plus independent review needs a bounded wait beyond ordinary reads. */
fun apiReadTimeout(method: String, path: String): Int = when {
    method == "POST" && (path == "/v1/mastery/diagnostics" || path.endsWith("/quizzes") ||
        path.endsWith("/practice") || path.endsWith("/rewrite")) -> 135_000
    method == "GET" && path.endsWith("/source") -> 60_000
    else -> 30_000
}
