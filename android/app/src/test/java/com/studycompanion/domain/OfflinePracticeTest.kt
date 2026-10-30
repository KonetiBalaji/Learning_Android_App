package com.studycompanion.domain

import org.junit.Assert.*
import org.junit.Test
import kotlin.random.Random

class OfflinePracticeTest {
    private val passages = listOf(
        OfflinePassage("energy", "cells", 2, "Mitochondria produce usable energy through cellular respiration inside living cells."),
        OfflinePassage("protein", "cells", 3, "Ribosomes assemble proteins using instructions carried by messenger molecules."))

    @Test fun allTypesRemainExactGroundedRecallAcrossSeeds() {
        for (seed in 0..20) for (kind in listOf("multiple_choice", "true_false", "yes_no")) {
            val questions = OfflinePractice.generate(passages, 2, kind, Random(seed))
            assertEquals(setOf("energy", "protein"), questions.map { it.source.id }.toSet())
            questions.forEach { question ->
                assertEquals("cells", question.source.sectionId)
                assertTrue(question.source.page in 2..3)
                assertTrue(question.explanation.contains(question.source.text))
                assertEquals(question.choices.size, question.choices.map { it.lowercase() }.distinct().size)
                if (kind == "multiple_choice") {
                    val masked = question.prompt.substringAfter("\n“").dropLast(1)
                    assertEquals(question.source.text, masked.replace("_____", question.choices[question.answer]))
                } else {
                    val shown = question.prompt.substringAfter("\n“").dropLast(1)
                    assertEquals(shown == question.source.text, question.answer == 0)
                }
            }
        }
    }

    @Test fun duplicateSourcesAndInsufficientMaterialDoNotCreateFiller() {
        val duplicated = listOf(passages.first(), passages.first().copy(id = "duplicate"))
        assertEquals(1, OfflinePractice.generate(duplicated, 1, "multiple_choice").size)
        for (action in listOf<() -> Unit>(
            { OfflinePractice.generate(duplicated, 2, "multiple_choice") },
            { OfflinePractice.generate(emptyList(), 1, "multiple_choice") },
            { OfflinePractice.generate(passages, 0, "multiple_choice") },
            { OfflinePractice.generate(passages, 1, "unsupported") })) {
            var rejected = false
            try { action() } catch (_: IllegalArgumentException) { rejected = true }
            assertTrue(rejected)
        }
    }
}
