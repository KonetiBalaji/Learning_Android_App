package com.konetibalaji.learning

/** Generation plus independent review needs a bounded wait beyond ordinary reads. */
fun apiReadTimeout(method: String, path: String): Int =
    if (method == "POST" && (path == "/v1/mastery/diagnostics" || path.endsWith("/quizzes"))) 135_000 else 30_000
