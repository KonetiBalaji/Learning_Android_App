package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class FractionModelTest {
    @Test fun defaultModelMakesOneWhole() {
        val model = FractionModel()
        assertEquals(4, model.numerator)
        assertEquals("1", model.simplified)
        assertEquals(1, model.wholeParts)
        assertEquals(0, model.remainder)
    }
    @Test fun reducesFractionsAndHandlesZeroAndTwoWholes() {
        assertEquals("1/2", FractionModel(8, 3, 1).simplified)
        assertEquals("0", FractionModel(8, 0, 0).simplified)
        assertEquals("2", FractionModel(8, 8, 8).simplified)
        assertEquals("3/2", FractionModel(4, 3, 3).simplified)
    }
    @Test fun reducingDenominatorClampsBothNumerators() {
        assertEquals(FractionModel(3, 3, 3), FractionModel(12, 10, 8).withDenominator(3))
    }
    @Test fun validatesLimits() {
        assertThrows(IllegalArgumentException::class.java) { FractionModel(0, 0, 0) }
        assertThrows(IllegalArgumentException::class.java) { FractionModel(4, 5, 0) }
        assertThrows(IllegalArgumentException::class.java) { FractionModel(4, 0, -1) }
    }
    @Test fun everySupportedCombinationPreservesWholeAndRemainder() {
        for (denominator in 2..12) for (left in 0..denominator) for (right in 0..denominator) {
            val model = FractionModel(denominator, left, right)
            assertEquals(left + right, model.wholeParts * denominator + model.remainder)
            assertTrue(model.remainder in 0 until denominator)
            val reduced = model.simplified.split('/')
            val top = reduced[0].toInt()
            val bottom = reduced.getOrNull(1)?.toInt() ?: 1
            assertEquals((left + right) * bottom, top * denominator)
        }
    }
}
