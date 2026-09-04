package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class CurriculumCatalogTest {
    private fun catalog(grade: Int = 8): CurriculumCatalogClient {
        val subjects = listOf(
            LearningSubject("math", "Mathematics", "∑", 0, 0),
            LearningSubject("science", "Science", "⚗", 0, 0),
            LearningSubject("english", "English", "Aa", 0, 0),
            LearningSubject("social", "Social Studies", "◎", 0, 0),
        )
        return CurriculumCatalogClient("foundation-2026-09", grade, "unconfirmed", subjects,
            subjects.associate { it.id to listOf(MasteryChapter("intro", "Introduction", 0)) })
    }

    @Test fun acceptsExactVersionedGradeScopedCatalog() {
        assertEquals("foundation-2026-09", validatedCatalog(catalog(), 8).version)
    }

    @Test fun rejectsWrongGradeBoardSubjectOrderAndMissingChapterMap() {
        assertThrows(IllegalArgumentException::class.java) { validatedCatalog(catalog(7), 8) }
        assertThrows(IllegalArgumentException::class.java) { validatedCatalog(catalog().copy(board = "invented"), 8) }
        assertThrows(IllegalArgumentException::class.java) { validatedCatalog(catalog().copy(subjects = catalog().subjects.reversed()), 8) }
        assertThrows(IllegalArgumentException::class.java) { validatedCatalog(catalog().copy(chapters = catalog().chapters - "social"), 8) }
    }

    @Test fun rejectsDuplicateOrBlankChapterIdentity() {
        val base = catalog()
        val duplicate = listOf(MasteryChapter("same", "One", 0), MasteryChapter("same", "Two", 0))
        assertThrows(IllegalArgumentException::class.java) {
            validatedCatalog(base.copy(chapters = base.chapters + ("math" to duplicate)), 8)
        }
        assertThrows(IllegalArgumentException::class.java) {
            validatedCatalog(base.copy(chapters = base.chapters + ("math" to listOf(MasteryChapter("", "", 0)))), 8)
        }
    }
}
