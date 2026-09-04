package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class WeeklyReadinessTest {
    @Test
    fun insufficientEvidenceNeverDisplaysNumericScore() {
        assertEquals("Not enough evidence", learningIndicatorText(100, "Insufficient evidence"))
    }

    @Test
    fun evidenceBackedIndicatorDisplaysScoreAndLabel() {
        assertEquals("76% · Developing", learningIndicatorText(76, "Developing"))
    }
}
