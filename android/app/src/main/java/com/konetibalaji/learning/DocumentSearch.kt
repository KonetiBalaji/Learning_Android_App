package com.konetibalaji.learning

import java.util.Locale

data class SourceSearchHit(val chapterId: String, val title: String, val start: Int, val end: Int,
    val text: String, val matchStart: Int, val matchEnd: Int, val truncated: Boolean)
data class DocumentSearch(val documentId: String, val query: String, val chapterIds: Set<String>,
    val hits: List<SourceSearchHit>, val hasMore: Boolean, val matchMode: String)

private val topicStopWords = setOf("a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "explain", "for", "from", "how", "in", "is", "it", "of", "on", "or", "show", "that", "the", "this",
    "to", "what", "when", "where", "which", "who", "why", "with", "work", "works")

private fun topicTerms(query: String): List<String> = Regex("[\\p{L}\\p{N}]+").findAll(query.lowercase(Locale.ROOT))
    .map { it.value }.filter { it.length >= 2 && it !in topicStopWords }.distinct().take(8).toList()

fun validSourceQuery(value: String): Boolean {
    val query = value.trim()
    return query.codePointCount(0, query.length) in 2..120 && query.none { it.code < 32 }
}

fun documentSearchStatus(result: DocumentSearch): String = when {
    result.hits.isEmpty() -> "No relevant source passage was found. Try different words or chapters; no selection was changed."
    result.matchMode == "literal_case_insensitive" -> "${result.hits.size} source ${if (result.hits.size == 1) "passage" else "passages"} found by exact phrase. Read a passage before using it as an excerpt."
    result.matchMode == "all_query_terms_case_insensitive" -> "${result.hits.size} source ${if (result.hits.size == 1) "passage" else "passages"} found by all topic words. Read a passage before using it as an excerpt."
    else -> "${result.hits.size} semantically related source ${if (result.hits.size == 1) "passage" else "passages"} found. Verify the wording before using a passage as an excerpt."
}

fun validateSourceSearch(result: DocumentSearch, documentId: String, query: String,
                         chapterIds: Set<String>): DocumentSearch {
    require(result.matchMode in setOf("literal_case_insensitive", "all_query_terms_case_insensitive", "semantic_embedding") &&
        result.documentId == documentId &&
        result.query == query.trim() && result.chapterIds == chapterIds && chapterIds.isNotEmpty()) { "Search response does not match the request" }
    require(result.hits.size <= 20 && (!result.hasMore || result.hits.isNotEmpty())) { "Invalid search result count" }
    result.hits.forEach { hit ->
        require(hit.chapterId in chapterIds && hit.start >= 0 && hit.end > hit.start)
        val length = hit.text.codePointCount(0, hit.text.length)
        require(length in 1..2000 && hit.end.toLong() - hit.start == length.toLong()) { "Invalid search source range" }
        require(hit.matchStart >= hit.start && hit.matchEnd > hit.matchStart && hit.matchEnd <= hit.end)
        val first = hit.text.offsetByCodePoints(0, hit.matchStart - hit.start)
        val last = hit.text.offsetByCodePoints(0, hit.matchEnd - hit.start)
        val matched = hit.text.substring(first, last)
        if (result.matchMode == "literal_case_insensitive") {
            require(matched.equals(result.query, ignoreCase = true)) { "Search match does not match the query" }
        } else if (result.matchMode == "all_query_terms_case_insensitive") {
            val terms = topicTerms(result.query)
            require(terms.size >= 2 && terms.all { term ->
                Regex("(?<![\\p{L}\\p{N}_])${Regex.escape(term)}(?![\\p{L}\\p{N}_])", RegexOption.IGNORE_CASE)
                    .containsMatchIn(matched)
            }) { "Topic result does not contain every query term" }
        } else {
            require(hit.matchStart == hit.start && hit.matchEnd == hit.end) {
                "Semantic result must identify the complete verbatim passage"
            }
        }
    }
    require(result.hits.zipWithNext().all { (left, right) -> left.start <= right.start }) { "Search results are out of order" }
    return result
}

fun selectedSearchExcerpt(result: DocumentSearch, documentId: String, chapters: Set<String>, index: Int): DocumentExcerpt {
    require(result.documentId == documentId && result.chapterIds == chapters) { "Search results are stale; search again" }
    val hit = result.hits.getOrNull(index) ?: error("Search result is no longer available")
    return DocumentExcerpt(hit.chapterId, hit.start, hit.end)
}
