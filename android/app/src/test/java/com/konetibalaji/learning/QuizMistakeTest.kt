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
}
