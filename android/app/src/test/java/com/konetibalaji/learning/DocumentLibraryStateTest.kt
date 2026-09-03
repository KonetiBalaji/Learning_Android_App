package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentLibraryStateTest {
    private val first = StudyDocument("first", "first.txt", emptyList())
    private val second = StudyDocument("second", "second.txt", emptyList())
    private val current = AppUiState(document = first, documentLibrary = listOf(first, second),
        quizId = "quiz", selectedChapterId = "chapter", canResumeDocumentQuiz = true,
        masterySessionId = "adaptive", accountEmail = "test@example.com")

    @Test fun deletingActiveDocumentClearsItsResumeStateOnly() {
        val result = stateAfterDocumentDeletion(current, first.id)
        assertEquals(listOf(second), result.documentLibrary)
        assertNull(result.document)
        assertNull(result.quizId)
        assertNull(result.selectedChapterId)
        assertFalse(result.canResumeDocumentQuiz)
        assertEquals("adaptive", result.masterySessionId)
        assertEquals(current.accountEmail, result.accountEmail)
    }

    @Test fun deletingOtherDocumentPreservesActiveQuiz() {
        assertEquals(current.copy(documentLibrary = listOf(first)), stateAfterDocumentDeletion(current, second.id))
    }

    @Test fun repeatedDeletionDoesNotChangeOtherState() {
        val deleted = stateAfterDocumentDeletion(current, first.id)
        assertEquals(deleted, stateAfterDocumentDeletion(deleted, first.id))
    }
}
