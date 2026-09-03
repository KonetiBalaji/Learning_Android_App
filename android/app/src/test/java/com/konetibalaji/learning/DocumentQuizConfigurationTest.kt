package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentQuizConfigurationTest {
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
