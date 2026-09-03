package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentSearchTest {
    private val hit = SourceSearchHit("chapter", "Source", 10, 16, "😀 CELL", 12, 16, false)
    private val result = DocumentSearch("doc", "cell", setOf("chapter"), listOf(hit), false)
    private fun validate(value: DocumentSearch) = validateSourceSearch(value, "doc", " cell ", setOf("chapter"), "literal_case_insensitive")

    @Test fun validatesExactUnicodeOffsetsAndCaseInsensitiveMatch() {
        assertEquals(result, validate(result))
        assertEquals(DocumentExcerpt("chapter", 10, 16), selectedSearchExcerpt(result, "doc", setOf("chapter"), 0))
    }

    @Test fun queryLimitsCountCodePointsAndRejectControls() {
        assertTrue(validSourceQuery("😀😀"))
        assertTrue(validSourceQuery("😀".repeat(120)))
        listOf("", "a", "   ", "a\nb", "a\tb", "😀".repeat(121)).forEach { assertFalse(validSourceQuery(it)) }
    }

    @Test fun rejectsWrongDocumentQueryModeAndUnselectedChapter() {
        listOf(result.copy(documentId = "other"), result.copy(query = "wrong"),
            result.copy(chapterIds = setOf("other")), result.copy(hits = listOf(hit.copy(chapterId = "other")))).forEach {
            assertThrows(IllegalArgumentException::class.java) { validate(it) }
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateSourceSearch(result, "doc", "cell", setOf("chapter"), "semantic")
        }
    }

    @Test fun rejectsMalformedPassagesAndMismatchedQuotedMatch() {
        listOf(hit.copy(start = -1), hit.copy(end = 17), hit.copy(text = ""),
            hit.copy(matchStart = 9), hit.copy(matchEnd = 17), hit.copy(matchEnd = 12),
            hit.copy(text = "😀 xxxx"), hit.copy(text = "x".repeat(2001), end = 2011)).forEach {
            assertThrows(IllegalArgumentException::class.java) { validate(result.copy(hits = listOf(it))) }
        }
    }

    @Test fun emptyResultsStayEmptyAndLimitsFailClosed() {
        assertTrue(validate(result.copy(hits = emptyList())).hits.isEmpty())
        assertThrows(IllegalArgumentException::class.java) { validate(result.copy(hits = emptyList(), hasMore = true)) }
        assertThrows(IllegalArgumentException::class.java) { validate(result.copy(hits = List(21) { hit })) }
        assertThrows(IllegalStateException::class.java) { selectedSearchExcerpt(result.copy(hits = emptyList()), "doc", setOf("chapter"), 0) }
    }

    @Test fun selectionCannotUseResultsFromOtherDocumentOrChapterSelection() {
        assertThrows(IllegalArgumentException::class.java) { selectedSearchExcerpt(result, "other", setOf("chapter"), 0) }
        assertThrows(IllegalArgumentException::class.java) { selectedSearchExcerpt(result, "doc", setOf("chapter", "extra"), 0) }
    }

    @Test fun deletingActiveDocumentClearsQueryAndSourceResults() {
        val state = AppUiState(document = StudyDocument("doc", "Name", emptyList()), sourceQuery = "cell", documentSearch = result)
        val deleted = stateAfterDocumentDeletion(state, "doc")
        assertEquals("", deleted.sourceQuery)
        assertNull(deleted.documentSearch)
        assertEquals(result, stateAfterDocumentDeletion(state, "other").documentSearch)
    }
}
