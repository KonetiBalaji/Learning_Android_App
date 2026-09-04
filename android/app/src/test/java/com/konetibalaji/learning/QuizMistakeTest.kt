package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class QuizMistakeTest {
    private val question = QuizQuestion("q1", 2, "What releases energy?", listOf("Ribosome", "Mitochondria"), "Cells")

    @Test fun completeMistakeCanBeReviewed() {
        val value = QuizMistake(question, "Ribosome", "Mitochondria", "Mitochondria release usable energy.")
        assertEquals(value, validateQuizMistake(value))
    }

    @Test fun malformedOrNonMistakeResultsAreRejected() {
        val valid = QuizMistake(question, "Ribosome", "Mitochondria", "Explanation")
        assertThrows(IllegalArgumentException::class.java) { validateQuizMistake(valid.copy(selectedOption = "Unknown")) }
        assertThrows(IllegalArgumentException::class.java) { validateQuizMistake(valid.copy(correctOption = "Unknown")) }
        assertThrows(IllegalArgumentException::class.java) { validateQuizMistake(valid.copy(selectedOption = "Mitochondria")) }
        assertThrows(IllegalArgumentException::class.java) { validateQuizMistake(valid.copy(explanation = " ")) }
    }

    @Test fun retryIdentitySurvivesResponseLossAndRequiresDurableStorage() {
        val id = "12345678-1234-4234-8234-123456789012"
        var disk: String? = null
        assertEquals(id, prepareMistakeRetry(disk, { disk = it; true }, { id }))
        assertEquals(id, prepareMistakeRetry(disk, { true }, { error("Must reuse saved request") }))
        assertThrows(IllegalArgumentException::class.java) { prepareMistakeRetry("broken", { true }) }
        assertThrows(IllegalStateException::class.java) { prepareMistakeRetry(null, { false }, { id }) }
    }
}
