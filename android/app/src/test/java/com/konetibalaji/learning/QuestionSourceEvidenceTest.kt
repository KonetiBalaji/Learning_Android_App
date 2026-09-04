package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class QuestionSourceEvidenceTest {
    private val png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    private val valid = QuestionSourceEvidence("quiz", "question",
        "Cells (source characters 10-20)", 10, 20, "0123456789",
        listOf(OriginalPdfPageEvidence(2, "image/png", png)))

    @Test fun exactOwnedEvidenceIsAccepted() {
        assertEquals(valid, validateQuestionSourceEvidence(valid, "quiz", "question"))
    }

    @Test fun mismatchedIdentityRangeOrReferenceFailsClosed() {
        assertThrows(IllegalArgumentException::class.java) {
            validateQuestionSourceEvidence(valid.copy(quizId = "other"), "quiz", "question")
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateQuestionSourceEvidence(valid.copy(end = 21), "quiz", "question")
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateQuestionSourceEvidence(valid.copy(reference = "Cells"), "quiz", "question")
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateQuestionSourceEvidence(valid.copy(originalPdfPages = listOf(
                OriginalPdfPageEvidence(2, "image/jpeg", png))), "quiz", "question")
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateQuestionSourceEvidence(valid.copy(originalPdfPages = listOf(
                OriginalPdfPageEvidence(2, "image/png", "not-base64"))), "quiz", "question")
        }
    }
}
