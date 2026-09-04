package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class InteractiveLessonExplorerTest {
    @Test fun routesOnlySupportedSubjectChapterPairs() {
        assertEquals(ExplorerKind.FRACTIONS, explorerKind("math", "fractions"))
        assertEquals(ExplorerKind.CELL_ORGANELLES, explorerKind("science", "cells"))
        assertEquals(ExplorerKind.SENTENCE_PARTS, explorerKind("english", "grammar"))
        assertNull(explorerKind("science", "fractions"))
        assertNull(explorerKind("math", "cells"))
        assertNull(explorerKind("english", "cells"))
        assertNull(explorerKind(null, null))
    }

    @Test fun curatedOrganelleLessonsAreDistinctAndInstructional() {
        assertEquals(3, organelleLessons.size)
        assertEquals(3, organelleLessons.map { it.name }.toSet().size)
        organelleLessons.forEach {
            assertTrue(it.function.length >= 40)
            assertTrue(it.evidence.length >= 40)
        }
    }

    @Test fun sentencePartsMapOneCompleteSentenceWithoutOverlap() {
        assertEquals(listOf("Subject", "Verb", "Object"), sentencePartLessons.map { it.name })
        assertEquals("The curious student solved the puzzle", sentencePartLessons.joinToString(" ") { it.words })
        sentencePartLessons.forEach {
            assertTrue(it.role.length >= 35)
            assertTrue(it.check.startsWith("Ask:"))
        }
    }
}
