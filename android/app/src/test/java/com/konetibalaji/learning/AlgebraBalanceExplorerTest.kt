package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AlgebraBalanceExplorerTest {
    @Test fun operationsPreserveTheEquationAndEndWithSubstitutionEvidence() {
        assertEquals(listOf("Start", "Subtract 3 from both sides", "Divide both sides by 2", "Check x = 4"),
            algebraBalanceSteps.map { it.operation })
        assertEquals(listOf("2x + 3", "2x", "x", "2 × 4 + 3"), algebraBalanceSteps.map { it.left })
        assertEquals(listOf("11", "8", "4", "11"), algebraBalanceSteps.map { it.right })
        assertTrue(algebraBalanceSteps[1].reason.contains("both sides"))
        assertTrue(algebraBalanceSteps[2].reason.contains("nonzero"))
        assertTrue(algebraBalanceSteps.last().reason.contains("8 + 3 = 11"))
    }
}
