package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class InteractiveLessonExplorerTest {
    private val lesson = TutorLesson("Equal-sized parts", "Keep equal denominators.",
        "2/5 + 1/5 = 3/5", "Keep the denominator 5.", "What is 1/5 + 3/5?")

    @Test fun everyTutorLessonHasThreeLearnerControlledStagesWithNonSubmissionDisclosure() {
        assertEquals(listOf("1. Understand", "2. Worked example", "3. Try the hint"),
            LessonStage.entries.map { it.label })
        assertEquals("Equal-sized parts", lessonStageContent(lesson, LessonStage.CONCEPT).heading)
        assertEquals(lesson.explanation, lessonStageContent(lesson, LessonStage.CONCEPT).body)
        assertEquals(lesson.workedExample, lessonStageContent(lesson, LessonStage.EXAMPLE).body)
        assertEquals(lesson.hint, lessonStageContent(lesson, LessonStage.HINT).body)
        assertTrue(lessonStageContent(lesson, LessonStage.HINT).guidance.contains("does not submit"))
    }

    @Test fun routesOnlySupportedSubjectChapterPairs() {
        assertEquals(ExplorerKind.FRACTIONS, explorerKind("math", "fractions"))
        assertEquals(ExplorerKind.DECIMAL_PLACE_VALUE, explorerKind("math", "decimals"))
        assertEquals(ExplorerKind.CELL_ORGANELLES, explorerKind("science", "cells"))
        assertEquals(ExplorerKind.SENTENCE_PARTS, explorerKind("english", "grammar"))
        assertEquals(ExplorerKind.MAP_COORDINATES, explorerKind("social", "geography"))
        assertNull(explorerKind("science", "fractions"))
        assertNull(explorerKind("science", "decimals"))
        assertNull(explorerKind("math", "cells"))
        assertNull(explorerKind("english", "cells"))
        assertNull(explorerKind("science", "geography"))
        assertNull(explorerKind(null, null))
    }

    @Test fun decimalPlacesMapEveryDigitToItsExactPositionalValue() {
        assertEquals(listOf("Tens", "Ones", "Tenths", "Hundredths", "Thousandths"),
            decimalPlaceLessons.map { it.name })
        assertEquals(listOf('4', '2', '3', '7', '5'), decimalPlaceLessons.map { it.digit })
        assertEquals(listOf(0, 1, 3, 4, 5), decimalPlaceLessons.map { it.characterIndex })
        assertEquals(listOf("40", "2", "0.3", "0.07", "0.005"), decimalPlaceLessons.map { it.value })
        assertTrue(decimalPlaceLessons.all { it.check.contains("means") && it.check.contains("=") })
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

    @Test fun coordinateReferencesUseCanonicalZeroLinesAndOrdering() {
        assertEquals(listOf("Equator", "Prime Meridian", "Coordinates"), mapLineLessons.map { it.name })
        assertEquals("0° latitude", mapLineLessons[0].value)
        assertEquals("0° longitude", mapLineLessons[1].value)
        assertTrue(mapLineLessons[2].role.contains("latitude first"))
        assertTrue(mapLineLessons[2].check.contains("north") && mapLineLessons[2].check.contains("east"))
    }
}
