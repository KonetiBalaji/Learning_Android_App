package com.konetibalaji.learning

fun acceptedSpeech(success: Boolean, alternatives: List<String>?): String? =
    if (success) alternatives?.firstOrNull { it.isNotBlank() }?.trim()?.take(6000) else null

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
