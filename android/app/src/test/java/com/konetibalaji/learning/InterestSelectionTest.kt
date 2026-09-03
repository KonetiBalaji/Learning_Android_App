package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class InterestSelectionTest {
    @Test fun selectedInterestCanBeRemovedAtTheLimit() {
        assertEquals(listOf("sports", "art"), toggleInterest(listOf("sports", "music", "art"), "music"))
    }
    @Test fun unknownChoicesAndFourthChoicesAreRejected() {
        val selected = listOf("sports", "music", "art")
        assertEquals(selected, toggleInterest(selected, "space"))
        assertEquals(emptyList<String>(), toggleInterest(emptyList(), "arbitrary text"))
    }
    @Test fun choicesCanBeAddedWithoutDuplicates() {
        assertEquals(listOf("space"), toggleInterest(emptyList(), "space"))
        assertEquals(emptyList<String>(), toggleInterest(listOf("space"), "space"))
    }
}
