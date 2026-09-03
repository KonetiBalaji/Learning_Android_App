package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class ChapterUnlocksTest {
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
