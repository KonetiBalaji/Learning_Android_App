package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentStructureRepairTest {
    private val chapter = Chapter("old", "Chapter 1", 0.85f)
    private val original = StudyDocument("doc", "Source.txt", listOf(chapter))
    private val current = AppUiState(document = original, selectedChapterIds = setOf("old"),
        documentQuestionCountInput = "15", documentDifficulty = "hard", documentQuestionType = "yes_no")

    @Test fun repairPreservesSettingsSelectionAndRequestFingerprint() {
        val recovered = Chapter("recovered", "Previously omitted text", 0.35f)
        val repaired = original.copy(chapters = listOf(recovered, chapter))
        val result = stateAfterStructureRepair(current, repaired)
        assertEquals(current.copy(document = repaired, documentRepairNotice = result.documentRepairNotice), result)
        assertEquals(current.selectedChapterIds, result.selectedChapterIds)
        assertTrue(result.documentRepairNotice!!.contains("not selected"))
        fun fingerprint(state: AppUiState) = quizCreationFingerprint(state.document!!.id,
            state.selectedChapterIds.sorted(), 15, state.documentDifficulty, state.documentQuestionType)
        assertEquals(fingerprint(current), fingerprint(result))
        assertTrue(stateAfterStructureRepair(result, repaired).documentRepairNotice!!.startsWith("No omitted"))
    }

    @Test fun emptySelectionRemainsEmpty() {
        assertEquals(emptySet<String>(), stateAfterStructureRepair(current.copy(selectedChapterIds = emptySet()), original).selectedChapterIds)
    }

    @Test fun unsafeResponsesAreRejected() {
        listOf(original.copy(id = "other"), original.copy(chapters = emptyList()),
            original.copy(chapters = listOf(chapter, chapter)),
            original.copy(chapters = listOf(chapter.copy(title = "changed")))) .forEach { response ->
            assertThrows(IllegalArgumentException::class.java) { stateAfterStructureRepair(current, response) }
        }
        val second = Chapter("second", "Chapter 2", 0.85f)
        assertThrows(IllegalArgumentException::class.java) {
            stateAfterStructureRepair(current.copy(document = original.copy(chapters = listOf(chapter, second))),
                original.copy(chapters = listOf(second, chapter)))
        }
    }
}
