package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class DocumentChapterSelectionTest {
    @Test fun newDocumentDefaultsToFirstChapter() {
        assertEquals(setOf("a"), restoredChapterSelection(null, listOf("a", "b")))
    }
    @Test fun selectedChaptersRestoreInSourceOrder() {
        assertEquals(listOf("a", "c"), restoredChapterSelection(setOf("c", "a"), listOf("a", "b", "c")).toList())
    }
    @Test fun clearingAndMissingIdsNeverSelectAnotherChapter() {
        assertEquals(emptySet<String>(), restoredChapterSelection(emptySet(), listOf("a")))
        assertEquals(emptySet<String>(), restoredChapterSelection(setOf("missing"), listOf("a")))
        assertEquals(emptySet<String>(), restoredChapterSelection(setOf("missing", "a"), listOf("a")))
    }
}
