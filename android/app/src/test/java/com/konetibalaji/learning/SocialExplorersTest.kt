package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class SocialExplorersTest {
    @Test fun historicalSourcesSeparateClassificationReasonAndLimitation() {
        assertEquals(listOf("Primary source", "Primary source", "Secondary source"),
            historicalSources.map { it.classification })
        assertTrue(historicalSources.all { it.reasoning.isNotBlank() && it.limitation.isNotBlank() })
        assertTrue(historicalSources.last().reasoning.contains("interprets"))
    }

    @Test fun civicModelIsOrderedAndDoesNotClaimOneJurisdiction() {
        assertEquals(listOf("Proposal", "Public input", "Decision", "Implementation and review"), civicStages.map { it.name })
        assertTrue(civicStages[1].purpose.contains("perspectives"))
        assertTrue(civicStages.last().purpose.contains("lawful channels"))
    }

    @Test fun marketExamplesDeriveShortageBalanceAndSurplus() {
        assertEquals(listOf(MarketState.SHORTAGE, MarketState.BALANCED, MarketState.SURPLUS), marketExamples.map { it.state })
        assertEquals(listOf(8, 0, 8), marketExamples.map { it.difference })
        assertThrows(IllegalArgumentException::class.java) { MarketExample(0, 2, 2) }
        assertThrows(IllegalArgumentException::class.java) { MarketExample(2, -1, 2) }
    }
}
