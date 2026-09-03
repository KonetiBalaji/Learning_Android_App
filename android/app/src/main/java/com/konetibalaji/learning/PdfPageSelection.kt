package com.konetibalaji.learning

data class OriginalPdfPage(val number: Int, val start: Int, val end: Int, val hasText: Boolean)
data class PdfPageCatalog(val documentId: String, val pages: List<OriginalPdfPage>)
data class PdfPageScope(val documentId: String, val first: Int, val last: Int,
    val chapterIds: List<String>, val excerpts: List<DocumentExcerpt>, val emptyPages: List<Int>)

fun validatePdfPageCatalog(catalog: PdfPageCatalog, documentId: String): PdfPageCatalog {
    require(catalog.documentId == documentId && catalog.pages.size in 1..1000) { "Invalid PDF page index" }
    var expectedStart = 0L
    catalog.pages.forEachIndexed { index, page ->
        require(page.number == index + 1 && page.start.toLong() == expectedStart &&
            page.end >= page.start && page.end <= 2_000_000 && page.end.toLong() - page.start <= 200_000 &&
            (!page.hasText || page.end > page.start)) { "PDF page boundaries are inconsistent" }
        expectedStart = page.end.toLong() + 1
    }
    return catalog
}

fun validPdfPageRange(first: String, last: String, total: Int): Pair<Int, Int>? {
    if (!first.matches(Regex("[0-9]{1,4}")) || !last.matches(Regex("[0-9]{1,4}"))) return null
    val from = first.toIntOrNull() ?: return null
    val to = last.toIntOrNull() ?: return null
    return if (from in 1..to && to <= total) from to to else null
}

fun validatePdfPageScope(scope: PdfPageScope, catalog: PdfPageCatalog, first: Int, last: Int,
                         availableChapters: Set<String>): PdfPageScope {
    validatePdfPageCatalog(catalog, scope.documentId)
    require(scope.first == first && scope.last == last && first in 1..last && last <= catalog.pages.size) { "PDF selection does not match requested pages" }
    val selected = catalog.pages.subList(first - 1, last)
    require(selected.any { it.hasText }) { "Selected pages have no extractable text" }
    require(scope.emptyPages == selected.filterNot { it.hasText }.map { it.number }) { "PDF empty-page report does not match the index" }
    require(scope.excerpts.isNotEmpty() && scope.excerpts == canonicalExcerpts(scope.excerpts)) { "Invalid PDF source ranges" }
    require(scope.chapterIds == scope.excerpts.map { it.chapterId } && scope.chapterIds.distinct() == scope.chapterIds &&
        availableChapters.containsAll(scope.chapterIds)) { "PDF selection references unexpected chapters" }
    require(scope.excerpts.all { it.start >= selected.first().start && it.end <= selected.last().end }) { "PDF source ranges escape the requested pages" }
    require(selected.filter { it.hasText }.all { page -> scope.excerpts.any { it.start < page.end && it.end > page.start } }) { "PDF selection omitted a page with text" }
    return scope
}
