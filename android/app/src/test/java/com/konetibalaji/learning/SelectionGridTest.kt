package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class SelectionGridTest {
    @Test fun columnsRespondToWidthAndFontWithoutAddingMoreAtSmallFonts() {
        assertEquals(3, selectionGridColumns(360f, 1f, 96f, 3))
        assertEquals(2, selectionGridColumns(360f, 1.5f, 96f, 3))
        assertEquals(1, selectionGridColumns(360f, 2f, 96f, 3))
        assertEquals(2, selectionGridColumns(360f, 1f, 160f, 2))
        assertEquals(1, selectionGridColumns(360f, 2f, 160f, 2))
        assertEquals(3, selectionGridColumns(1200f, 0.8f, 96f, 3))
        assertEquals(1, selectionGridColumns(0f, 1f, 96f, 3))
    }
    @Test fun invalidDimensionsFailExplicitly() {
        listOf(Float.NaN, Float.POSITIVE_INFINITY, -1f).forEach {
            assertThrows(IllegalArgumentException::class.java) { selectionGridColumns(it, 1f, 96f, 3) }
        }
        assertThrows(IllegalArgumentException::class.java) { selectionGridColumns(360f, 0f, 96f, 3) }
    }
}
