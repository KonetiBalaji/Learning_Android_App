package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class TutorConversationTest {
    private val pending = TutorChatTurn("id", "Why?", "pending", null, null)
    @Test fun updateReplacesPendingInsteadOfDuplicatingQuestion() {
        val completed = pending.copy(status = "complete", answer = "Equal parts.", supported = true)
        assertEquals(listOf(completed), mergeTutorTurn(listOf(pending), completed))
        assertEquals(listOf(pending), mergeTutorTurn(emptyList(), pending))
    }
    @Test fun unknownTransportOutcomeKeepsItsRequestIdentity() {
        val uncertain = PendingTutorQuestion("id", "Why?")
        assertEquals(uncertain, pendingTutorQuestion(emptyList(), uncertain))
        assertEquals(uncertain, pendingTutorQuestion(listOf(pending), null))
        assertNull(pendingTutorQuestion(listOf(pending.copy(status = "failed")), uncertain))
    }
    @Test(expected = IllegalArgumentException::class)
    fun incompleteSuccessIsNotAcknowledged() { pending.copy(status = "complete") }
    @Test(expected = IllegalArgumentException::class)
    fun failedReplyCannotExposePartialAnswer() { pending.copy(status = "failed", answer = "partial") }
    @Test fun questionLimitDoesNotSplitUnicodePair() {
        val text = "a".repeat(999) + "😀"
        assertEquals("a".repeat(999), boundedTutorQuestion(text))
        assertEquals("Why?", boundedTutorQuestion("Why?"))
    }
}
