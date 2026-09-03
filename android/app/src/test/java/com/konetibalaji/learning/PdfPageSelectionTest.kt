package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class PdfPageSelectionTest {
    private val catalog = PdfPageCatalog("doc", listOf(OriginalPdfPage(1, 0, 10, true),
        OriginalPdfPage(2, 11, 21, true), OriginalPdfPage(3, 22, 22, false)))
    private val scope = PdfPageScope("doc", 2, 3, listOf("chapter"), listOf(DocumentExcerpt("chapter", 11, 21)), listOf(3))
    private fun validate(value: PdfPageScope) = validatePdfPageScope(value, catalog, 2, 3, setOf("chapter"))

    @Test fun acceptsPhysicalPagesIncludingBlankPageAndExactExcerpt() {
        assertEquals(catalog, validatePdfPageCatalog(catalog, "doc"))
        assertEquals(scope, validate(scope))
    }
    @Test fun rejectsWrongDocumentAndMalformedPageIndexes() {
        assertThrows(IllegalArgumentException::class.java) { validatePdfPageCatalog(catalog, "other") }
        listOf(emptyList(), catalog.pages.reversed(), listOf(OriginalPdfPage(1, 1, 2, true)),
            listOf(OriginalPdfPage(1, 0, 0, true)), listOf(OriginalPdfPage(1, 0, -1, false)),
            listOf(OriginalPdfPage(1, 0, 200001, true)),
            listOf(catalog.pages[0], catalog.pages[1].copy(start = 10))).forEach {
            assertThrows(IllegalArgumentException::class.java) { validatePdfPageCatalog(catalog.copy(pages = it), "doc") }
        }
    }
    @Test fun validatesInclusivePageInputWithoutCoercion() {
        assertEquals(2 to 3, validPdfPageRange("2", "3", 3))
        listOf("0" to "1", "2" to "1", "1" to "4", "1.0" to "2", "" to "2", "1" to "-2", "1" to "99999").forEach {
            assertNull(validPdfPageRange(it.first, it.second, 3))
        }
    }
    @Test fun rejectsChangedIdentityPageRequestOrBlankPageReport() {
        listOf(scope.copy(documentId = "other"), scope.copy(first = 1), scope.copy(last = 2),
            scope.copy(emptyPages = emptyList()), scope.copy(emptyPages = listOf(2, 3))).forEach {
            assertThrows(IllegalArgumentException::class.java) { validate(it) }
        }
    }
    @Test fun rejectsEscapedEmptyUnknownOrOverlappingSourceRanges() {
        listOf(scope.copy(excerpts = emptyList()), scope.copy(excerpts = listOf(DocumentExcerpt("chapter", 10, 21))),
            scope.copy(excerpts = listOf(DocumentExcerpt("chapter", 11, 23))), scope.copy(chapterIds = listOf("unknown")),
            scope.copy(excerpts = scope.excerpts + scope.excerpts)).forEach {
            assertThrows(IllegalArgumentException::class.java) { validate(it) }
        }
    }
    @Test fun rejectsBlankOnlySelectionAndOmittedTextPage() {
        assertThrows(IllegalArgumentException::class.java) {
            validatePdfPageScope(scope.copy(first = 3), catalog, 3, 3, setOf("chapter"))
        }
        assertThrows(IllegalArgumentException::class.java) {
            validatePdfPageScope(scope.copy(first = 1), catalog, 1, 3, setOf("chapter"))
        }
    }
}
