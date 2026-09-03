package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentPreviewTest {
    private val preview = DocumentPreview("doc", "chapter", "Title", 0, 1, 10, 12, "🙂x")
    @Test fun acceptsUnicodeCodePointsRatherThanUtf16Length() {
        assertEquals(preview, validateDocumentPreview(preview, "doc", "chapter", 0))
    }
    @Test fun rejectsWrongSourcePageAndMalformedRanges() {
        listOf(preview.copy(documentId = "other"), preview.copy(chapterId = "other"),
            preview.copy(page = 1), preview.copy(totalPages = 0), preview.copy(start = -1),
            preview.copy(end = 11), preview.copy(text = ""),
            preview.copy(text = "x".repeat(2001), end = 2011)).forEach {
            assertThrows(IllegalArgumentException::class.java) { validateDocumentPreview(it, "doc", "chapter", 0) }
        }
    }
}
