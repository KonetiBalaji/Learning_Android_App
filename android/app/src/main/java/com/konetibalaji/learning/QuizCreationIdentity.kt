package com.konetibalaji.learning

import java.security.MessageDigest
import java.util.UUID

fun quizCreationFingerprint(documentId: String, chapterIds: List<String>, count: Int, difficulty: String, type: String, excerpts: List<DocumentExcerpt> = emptyList()): String {
    val parts = listOf(documentId, count.toString(), difficulty, type) + chapterIds.sorted() +
        if (excerpts.isEmpty()) emptyList() else listOf("excerpts-v1", encodeExcerpts(excerpts))
    val canonical = parts.joinToString("") { "${it.length}:$it" }
    return MessageDigest.getInstance("SHA-256").digest(canonical.toByteArray(Charsets.UTF_8))
        .joinToString("") { "%02x".format(it) }
}

fun prepareQuizCreation(
    saved: String?, fingerprint: String, persist: (String) -> Boolean,
    newId: () -> String = { UUID.randomUUID().toString() },
): String {
    val previous = saved?.split('|')
    if (previous != null) {
        require(previous.size == 2 && previous[1].matches(Regex("[0-9a-f]{64}")) &&
            runCatching { UUID.fromString(previous[0]).toString() == previous[0] }.getOrDefault(false)) {
            "Saved quiz request identity is invalid"
        }
    }
    val id = if (previous != null && previous[1] == fingerprint) previous[0] else newId()
    check(persist("$id|$fingerprint")) { "Could not save quiz request before submission" }
    return id
}
