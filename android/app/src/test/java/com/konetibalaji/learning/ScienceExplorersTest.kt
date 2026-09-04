package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ScienceExplorersTest {
    @Test fun matterModelsDistinguishSpacingAndMovement() {
        assertEquals(listOf("Solid", "Liquid", "Gas"), matterStates.map { it.name })
        assertEquals(3, matterStates.map { it.spacing }.toSet().size)
        assertEquals(3, matterStates.map { it.movement }.toSet().size)
    }

    @Test fun constantSpeedModelsComputeDistanceWithoutUnitMixing() {
        assertEquals(listOf(6, 12, 25), motionModels.map { it.distanceMetres })
        assertThrows(IllegalArgumentException::class.java) { MotionModel(0, 2) }
        assertThrows(IllegalArgumentException::class.java) { MotionModel(2, -1) }
    }

    @Test fun foodChainUsesExplicitTenPercentTransferExample() {
        assertEquals(listOf("Producer", "Primary consumer", "Secondary consumer", "Tertiary consumer"),
            ecosystemEnergyLevels.map { it.role })
        assertEquals(listOf(10_000, 1_000, 100, 10), ecosystemEnergyLevels.map { it.energyUnits })
        ecosystemEnergyLevels.zipWithNext().forEach { (lower, higher) ->
            assertEquals(lower.energyUnits / 10, higher.energyUnits)
        }
        assertTrue(ecosystemEnergyLevels.map { it.organism }.toSet().size == 4)
    }
}
