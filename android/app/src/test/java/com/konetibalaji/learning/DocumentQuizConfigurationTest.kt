package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentQuizConfigurationTest {
    @Test fun questionTypePreferenceOnlyRestoresSupportedChoices() {
        documentQuestionTypes.keys.forEach { assertEquals(it, restoredDocumentQuestionType(it)) }
        assertEquals("multiple_choice", restoredDocumentQuestionType(null))
        assertEquals("multiple_choice", restoredDocumentQuestionType("essay"))
    }
    @Test fun absentServerFormatIsNotInferredFromPreference() {
        assertEquals("Question type: unspecified", documentQuestionTypeLabel(null))
        assertEquals("Question type: unspecified", documentQuestionTypeLabel("unknown"))
        assertEquals("Question type: True / False", documentQuestionTypeLabel("true_false"))
        assertEquals("Question type: Yes / No", documentQuestionTypeLabel("yes_no"))
    }
    @Test fun difficultyPreferenceOnlyRestoresSupportedChoices() {
        documentDifficulties.keys.forEach { assertEquals(it, restoredDocumentDifficulty(it)) }
        assertEquals("easy", restoredDocumentDifficulty(null))
        assertEquals("easy", restoredDocumentDifficulty("expert"))
    }
    @Test fun legacyQuizDifficultyIsNotInferredFromCurrentPreference() {
        assertEquals("Requested difficulty: unspecified", requestedDifficultyLabel(null))
        assertEquals("Requested difficulty: unspecified", requestedDifficultyLabel("unknown"))
        assertTrue(requestedDifficultyLabel("hard").contains("Hard"))
    }
    @Test fun allSupportedCountsAreAccepted() {
        (5..20).forEach { assertEquals(it, validDocumentQuestionCount(it.toString())) }
        assertEquals(7, validDocumentQuestionCount(" 7 "))
    }
    @Test fun invalidCountsCannotGenerate() {
        listOf("", " ", "4", "21", "-5", "7.5", "five", "999999999999").forEach {
            assertNull(validDocumentQuestionCount(it))
        }
    }
}
