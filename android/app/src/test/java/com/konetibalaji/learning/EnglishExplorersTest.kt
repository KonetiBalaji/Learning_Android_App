package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EnglishExplorersTest {
    @Test fun inferenceSeparatesDetailClaimAndQuotedSupport() {
        assertEquals(listOf("Text detail", "Inference", "Supporting evidence"), readingEvidenceSteps.map { it.label })
        assertTrue(readingPassage.contains("cracked") && readingPassage.contains("watering cans"))
        assertTrue(readingEvidenceSteps[0].text.contains("cracked"))
        assertTrue(readingEvidenceSteps[1].text.contains("intends"))
        assertTrue(readingEvidenceSteps[2].text.contains("watering cans"))
    }

    @Test fun vocabularyModelReconstructsWordAndMeaning() {
        assertEquals("unhelpful", wordParts.joinToString("") { it.text.trim('-') })
        assertEquals(listOf("Prefix", "Root", "Suffix"), wordParts.map { it.label })
        assertEquals(listOf("not", "to assist", "full of or characterized by"), wordParts.map { it.meaning })
    }

    @Test fun paragraphHasOneOrderedSentenceForEachReasoningRole() {
        assertEquals(listOf("Topic sentence", "Evidence", "Explanation", "Concluding sentence"),
            paragraphParts.map { it.label })
        assertEquals(4, paragraphParts.map { it.sentence }.toSet().size)
        assertTrue(paragraphParts.all { it.sentence.endsWith('.') && it.purpose.endsWith('.') })
    }
}
