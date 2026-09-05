package com.konetibalaji.learning

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GradeAvailabilityTest {
    @Test fun onlyTheReviewedInitialGradeIsSelectable() {
        assertTrue(isSupportedGrade(8))
        ((1..12).toSet() - 8).forEach { assertFalse(isSupportedGrade(it)) }
    }
}
