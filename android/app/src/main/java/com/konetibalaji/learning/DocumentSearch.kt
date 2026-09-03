package com.konetibalaji.learning

data class SourceSearchHit(val chapterId: String, val title: String, val start: Int, val end: Int,
    val text: String, val matchStart: Int, val matchEnd: Int, val truncated: Boolean)
data class DocumentSearch(val documentId: String, val query: String, val chapterIds: Set<String>,
    val hits: List<SourceSearchHit>, val hasMore: Boolean)

fun validSourceQuery(value: String): Boolean {
    val query = value.trim()
    return query.codePointCount(0, query.length) in 2..120 && query.none { it.code < 32 }
}

fun validateSourceSearch(result: DocumentSearch, documentId: String, query: String,
                         chapterIds: Set<String>, mode: String): DocumentSearch {
    require(mode == "literal_case_insensitive" && result.documentId == documentId &&
        result.query == query.trim() && result.chapterIds == chapterIds && chapterIds.isNotEmpty()) { "Search response does not match the request" }
    require(result.hits.size <= 20 && (!result.hasMore || result.hits.isNotEmpty())) { "Invalid search result count" }
    result.hits.forEach { hit ->
        require(hit.chapterId in chapterIds && hit.start >= 0 && hit.end > hit.start)
        val length = hit.text.codePointCount(0, hit.text.length)
        require(length in 1..2000 && hit.end.toLong() - hit.start == length.toLong()) { "Invalid search source range" }
        require(hit.matchStart >= hit.start && hit.matchEnd > hit.matchStart && hit.matchEnd <= hit.end)
        val first = hit.text.offsetByCodePoints(0, hit.matchStart - hit.start)
        val last = hit.text.offsetByCodePoints(0, hit.matchEnd - hit.start)
        require(hit.text.substring(first, last).equals(result.query, ignoreCase = true)) { "Search match does not match the query" }
    }
    require(result.hits.zipWithNext().all { (left, right) -> left.start <= right.start }) { "Search results are out of order" }
    return result
}

fun selectedSearchExcerpt(result: DocumentSearch, documentId: String, chapters: Set<String>, index: Int): DocumentExcerpt {
    require(result.documentId == documentId && result.chapterIds == chapters) { "Search results are stale; search again" }
    val hit = result.hits.getOrNull(index) ?: error("Search result is no longer available")
    return DocumentExcerpt(hit.chapterId, hit.start, hit.end)
}
