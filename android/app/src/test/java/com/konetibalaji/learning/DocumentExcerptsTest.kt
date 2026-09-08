package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentExcerptsTest {
    private val preview = DocumentPreview("doc", "chapter", "Title", 0, 1, 10, 15, "😀abc ")

    @Test fun convertsEmojiAndReversedSelectionsToAbsoluteCodePoints() {
        assertEquals(DocumentExcerpt("chapter", 10, 14), excerptFromSelection(preview, 0, 5))
        assertEquals(DocumentExcerpt("chapter", 11, 14), excerptFromSelection(preview, 5, 2))
    }

    @Test fun rejectsSplitSurrogatesEmptyWhitespaceAndOutsideSelections() {
        listOf(0 to 1, 1 to 3, 2 to 2, 5 to 6, -1 to 2, 0 to 7).forEach { (start, end) ->
            assertThrows(IllegalArgumentException::class.java) { excerptFromSelection(preview, start, end) }
        }
    }

    @Test fun persistenceRoundTripPreservesDisjointRangesInSourceOrder() {
        val ranges = listOf(DocumentExcerpt("chapter-二", 20, 30), DocumentExcerpt("chapter", 10, 14))
        assertEquals(ranges.reversed(), decodeExcerpts(encodeExcerpts(ranges)))
        assertEquals(emptyList<DocumentExcerpt>(), decodeExcerpts(null))
    }

    @Test fun invalidSavedSelectionDoesNotBecomeWholeChapterMode() {
        listOf("", "broken", "a,1", "%%,1,3", "YQ,-1,4", "YQ,4,4", "YQ,1,5;YQ,4,8").forEach {
            assertThrows(IllegalArgumentException::class.java) { decodeExcerpts(it) }
        }
    }

    @Test fun overlapDuplicatesAndTooManyRangesAreRejected() {
        val one = DocumentExcerpt("a", 0, 4)
        assertThrows(IllegalArgumentException::class.java) { canonicalExcerpts(listOf(one, one)) }
        assertThrows(IllegalArgumentException::class.java) { canonicalExcerpts(listOf(one, one.copy(start = 3, end = 7))) }
        assertThrows(IllegalArgumentException::class.java) { canonicalExcerpts((0..50).map { DocumentExcerpt("a", it * 2, it * 2 + 1) }) }
        assertEquals(2, canonicalExcerpts(listOf(one, DocumentExcerpt("a", 4, 7))).size)
    }

    @Test fun overlapHasAnActionableLearnerMessage() {
        val failure = assertThrows(OverlappingDocumentExcerptsException::class.java) {
            canonicalExcerpts(listOf(DocumentExcerpt("chapter", 0, 20), DocumentExcerpt("chapter", 10, 30)))
        }
        assertEquals(
            "This passage overlaps your current excerpt. Clear the selection to replace it, or choose a different passage.",
            failure.message,
        )
    }

    @Test fun requestIdentityChangesWithScopeButNotExcerptOrder() {
        fun identity(excerpts: List<DocumentExcerpt>) = quizCreationFingerprint("doc", listOf("a"), 5, "easy", "multiple_choice", excerpts)
        val ranges = listOf(DocumentExcerpt("a", 0, 4), DocumentExcerpt("a", 10, 15))
        assertEquals(identity(ranges), identity(ranges.reversed()))
        assertNotEquals(identity(ranges), identity(emptyList()))
        assertNotEquals(identity(ranges), identity(listOf(ranges[0].copy(end = 3), ranges[1])))
        assertEquals(quizCreationFingerprint("doc", listOf("a"), 5, "easy", "multiple_choice"), identity(emptyList()))
    }

    @Test fun deletingMaterialClearsOnlyItsActiveExcerpts() {
        val excerpts = listOf(DocumentExcerpt("a", 0, 4))
        val state = AppUiState(document = StudyDocument("doc", "Name", emptyList()), documentExcerpts = excerpts)
        assertEquals(excerpts, stateAfterDocumentDeletion(state, "other").documentExcerpts)
        assertTrue(stateAfterDocumentDeletion(state, "doc").documentExcerpts.isEmpty())
    }
}
