package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class QuizCreationIdentityTest {
    private val id = "12345678-1234-4234-8234-123456789012"
    private fun fingerprint(count: Int = 10) = quizCreationFingerprint("doc", listOf("b", "a"), count, "easy", "yes_no")

    @Test fun savedIdentitySurvivesReconstructionForTheSameRequest() {
        var disk: String? = null
        assertEquals(id, prepareQuizCreation(disk, fingerprint(), { disk = it; true }, { id }))
        assertEquals(id, prepareQuizCreation(disk, fingerprint(), { disk = it; true }, { error("Do not allocate on retry") }))
        assertEquals(fingerprint(), quizCreationFingerprint("doc", listOf("a", "b"), 10, "easy", "yes_no"))
    }

    @Test fun changedSettingsGetANewIdentity() {
        val next = "87654321-1234-4234-8234-123456789012"
        assertEquals(next, prepareQuizCreation("$id|${fingerprint()}", fingerprint(5), { true }, { next }))
        listOf(
            quizCreationFingerprint("other", listOf("a", "b"), 10, "easy", "yes_no"),
            quizCreationFingerprint("doc", listOf("a"), 10, "easy", "yes_no"),
            quizCreationFingerprint("doc", listOf("a", "b"), 10, "hard", "yes_no"),
            quizCreationFingerprint("doc", listOf("a", "b"), 10, "easy", "true_false"),
        ).forEach { assertNotEquals(fingerprint(), it) }
    }

    @Test fun failedStorageCannotReturnAnIdentityForPosting() {
        assertThrows(IllegalStateException::class.java) {
            prepareQuizCreation(null, fingerprint(), { false }, { id })
        }
    }

    @Test fun corruptedPendingIdentityDoesNotSilentlyAllocateAnotherQuiz() {
        listOf("broken", "$id|bad", "not-a-uuid|${fingerprint()}").forEach { saved ->
            assertThrows(IllegalArgumentException::class.java) {
                prepareQuizCreation(saved, fingerprint(), { error("Do not overwrite") }, { error("Do not allocate") })
            }
        }
    }
}
