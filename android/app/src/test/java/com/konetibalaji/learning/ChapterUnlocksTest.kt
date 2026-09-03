package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class ChapterUnlocksTest {
    @Test fun deniedChapterLosesOnlyItsUnlockAndPreservesSavedLearning() {
        val snapshot = ProgressSnapshot(emptyMap(), emptyList(), emptyList(), unlockedChapterIds = setOf("math:geometry", "english:writing"))
        val state = AppUiState(unlockedChapterIds = snapshot.unlockedChapterIds, progressSnapshot = snapshot,
            masterySessionId = "saved-session", canResumeMastery = true, grade = 8, accountEmail = "learner@example.com")
        val denied = stateAfterChapterAccessDenied(state, "math:geometry")
        assertEquals(state.copy(unlockedChapterIds = setOf("english:writing"),
            progressSnapshot = snapshot.copy(unlockedChapterIds = setOf("english:writing"))), denied)
        assertEquals(denied, stateAfterChapterAccessDenied(denied, "math:geometry"))
        assertNull(stateAfterChapterAccessDenied(AppUiState(), "math:geometry").progressSnapshot)
    }
    @Test fun acceptsOnlyServerSuppliedUnlocks() {
        assertEquals(setOf("math:geometry"), serverChapterUnlocks(8, 8, listOf("math:geometry")))
        assertEquals(emptySet<String>(), serverChapterUnlocks(8, 8, emptyList()))
    }
    @Test fun legacyAndUnscopedResponsesGrantNoAccess() {
        assertEquals(emptySet<String>(), serverChapterUnlocks(8, null, listOf("math:geometry")))
        assertEquals(emptySet<String>(), serverChapterUnlocks(8, 8, null))
    }
    @Test fun rejectsWrongGradeDuplicatesAndMalformedIds() {
        assertThrows(IllegalArgumentException::class.java) { serverChapterUnlocks(8, 7, listOf("math:geometry")) }
        assertThrows(IllegalArgumentException::class.java) { serverChapterUnlocks(8, 8, listOf("math:geometry", "math:geometry")) }
        assertThrows(IllegalArgumentException::class.java) { serverChapterUnlocks(8, 8, listOf("geometry")) }
    }
}
