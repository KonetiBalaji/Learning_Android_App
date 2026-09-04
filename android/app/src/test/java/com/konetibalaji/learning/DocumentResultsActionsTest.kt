package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DocumentResultsActionsTest {
    @Test fun difficultyCanIncreaseOnlyThroughFixedOrderedLevels() {
        assertEquals("medium", nextDocumentDifficulty(null))
        assertEquals("medium", nextDocumentDifficulty("easy"))
        assertEquals("hard", nextDocumentDifficulty("medium"))
        assertNull(nextDocumentDifficulty("hard"))
        assertNull(nextDocumentDifficulty("mixed"))
    }
}
