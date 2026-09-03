package com.konetibalaji.learning

/** Bytes written to the request stream, not server acknowledgement or analysis completion. */
data class DocumentUploadProgress(val bytes: Long = 0, val declaredBytes: Long? = null, val awaitingAnalysis: Boolean = false) {
    init { require(bytes in 0..MAX_DOCUMENT_BYTES) }
    val fraction: Float? get() = declaredBytes?.takeIf { it > 0 && bytes <= it && !awaitingAnalysis }
        ?.let { (bytes.toDouble() / it).coerceAtMost(0.99).toFloat() }
    val title: String get() = if (awaitingAnalysis) "Waiting for document analysis…" else "Sending document…"
    val detail: String get() = if (awaitingAnalysis) "The file was sent. Waiting for the service to validate it and detect chapters."
        else "${(bytes + 1023) / 1024} KiB written${fraction?.let { " · estimated ${(it * 100).toInt()}%" }.orEmpty()}"
}
