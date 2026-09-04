package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class QuestionSourceEvidenceTest {
    private val valid = QuestionSourceEvidence("quiz", "question",
        "Cells (source characters 10-20)", 10, 20, "0123456789")

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
    }
}
