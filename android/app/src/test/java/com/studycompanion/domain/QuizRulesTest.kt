package com.studycompanion.domain

import org.junit.Assert.*
import org.junit.Test

class QuizRulesTest {
    @Test fun answerRequiresSelectionAndUnlockedQuestion() {
        assertFalse(QuizRules.canSubmit(null, false, false))
        assertFalse(QuizRules.canSubmit(0, true, false))
        assertFalse(QuizRules.canSubmit(0, false, true))
        assertTrue(QuizRules.canSubmit(0, false, false))
    }
    @Test fun countRejectsInvalidAndUnboundedInput() {
        listOf("", "a", "0", "51", "-1").forEach { assertNull(QuizRules.questionCount(it)) }
        assertEquals(10, QuizRules.questionCount("10"))
        assertEquals(50, QuizRules.questionCount("50"))
    }
}
