package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class TriangleAreaExplorerTest {
    @Test fun modelsComputeExactWholeNumberAreas() {
        assertEquals(listOf(6, 8, 10), triangleAreaModels.map { it.base })
        assertEquals(listOf(4, 5, 6), triangleAreaModels.map { it.height })
        assertEquals(listOf(12, 20, 30), triangleAreaModels.map { it.area })
    }

    @Test fun modelRejectsNonPositiveOrNonIntegralExamples() {
        assertThrows(IllegalArgumentException::class.java) { TriangleAreaModel(0, 4) }
        assertThrows(IllegalArgumentException::class.java) { TriangleAreaModel(3, 3) }
    }
}
