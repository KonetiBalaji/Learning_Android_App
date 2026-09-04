package com.konetibalaji.learning

private const val MAX_RECOGNIZED_TEXT_LENGTH = 6000

/** Accept only reviewable text from a successful recognition result. */
fun acceptedSpeech(success: Boolean, alternatives: List<String>?): String? {
    if (!success) return null
    return alternatives.orEmpty().asSequence()
        .map(::normalizeRecognizedText)
        .firstOrNull { it.isNotEmpty() }
}

private fun normalizeRecognizedText(value: String): String {
    val normalized = buildString(value.length.coerceAtMost(MAX_RECOGNIZED_TEXT_LENGTH)) {
        var pendingSpace = false
        var index = 0
        while (index < value.length && length <= MAX_RECOGNIZED_TEXT_LENGTH) {
            val codePoint = value.codePointAt(index)
            index += Character.charCount(codePoint)
            if (Character.isWhitespace(codePoint)) {
                pendingSpace = isNotEmpty()
            } else if (Character.isISOControl(codePoint)) {
                pendingSpace = isNotEmpty()
            } else {
                if (pendingSpace) append(' ')
                appendCodePoint(codePoint)
                pendingSpace = false
            }
        }
    }
    if (normalized.length <= MAX_RECOGNIZED_TEXT_LENGTH) return normalized
    var end = MAX_RECOGNIZED_TEXT_LENGTH
    if (normalized[end - 1].isHighSurrogate()) end--
    return normalized.substring(0, end).trimEnd()
}

fun speechChunks(text: String, limit: Int): List<String> {
    require(limit >= 2)
    val chunks = mutableListOf<String>()
    var start = 0
    while (start < text.length) {
        var end = minOf(start + limit, text.length)
        if (end < text.length && text[end - 1].isHighSurrogate()) end--
        chunks.add(text.substring(start, end))
        start = end
    }
    return chunks
}
