package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LearningNavigationTest {
    @Test fun conflictsRecoverTheSubmittedWorkflow() {
        assertEquals(SubmittedFlow.DOCUMENT, recoveryAfterFailure(409, SubmittedFlow.DOCUMENT))
        assertEquals(SubmittedFlow.MASTERY, recoveryAfterFailure(409, SubmittedFlow.MASTERY))
    }

    @Test fun resumeAndUnrelatedRequestsCannotStartARecoveryLoop() {
        assertNull(recoveryAfterFailure(409, null))
        for (status in listOf(null, 401, 403, 404, 422, 429, 500, 503)) {
            for (flow in SubmittedFlow.entries) assertNull(recoveryAfterFailure(status, flow))
        }
    }

    @Test fun restoredPhasesMatchServerState() {
        mapOf("diagnostic" to Screen.Diagnostic, "tutor" to Screen.Tutor,
            "practice" to Screen.Practice, "rewrite" to Screen.Rewrite,
            "mastered" to Screen.Mastery).forEach { (status, expected) ->
            assertEquals(expected, screenForMasteryStatus(status))
        }
    }

    @Test fun successfulRemediationContinuesAssessment() {
        assertEquals(Screen.Diagnostic, screenForLearningAction("next_question"))
        assertEquals(Screen.Tutor, screenForLearningAction("tutor"))
        assertEquals(Screen.Mastery, screenForLearningAction("mastery"))
    }

    @Test(expected = IllegalStateException::class)
    fun unknownPhaseCannotFallThroughToMastery() { screenForMasteryStatus("unknown") }

    @Test(expected = IllegalStateException::class)
    fun unknownActionCannotFallThroughToMastery() { screenForLearningAction("unknown") }
}
