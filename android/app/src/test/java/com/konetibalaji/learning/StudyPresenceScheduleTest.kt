package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class StudyPresenceScheduleTest {
    @Test fun startsFreshPulsesThenResetsOnStopSwitchOrDelay() {
        val schedule = StudyPresenceSchedule()
        assertEquals(PresenceCommand("a", true), schedule.next("a", 0))
        assertNull(schedule.next("a", 5_000))
        assertEquals(PresenceCommand("a", false), schedule.next("a", 15_000))
        assertNull(schedule.next(null, 20_000))
        assertEquals(PresenceCommand("a", true), schedule.next("a", 25_000))
        assertEquals(PresenceCommand("b", true), schedule.next("b", 30_000))
        assertEquals(PresenceCommand("b", true), schedule.next("b", 61_000))
        schedule.reset()
        assertEquals(PresenceCommand("b", true), schedule.next("b", 62_000))
        assertEquals(PresenceCommand("b", true), schedule.next("b", 1))
    }
    @Test fun excludesBackgroundIdleLoadingAndNonLearningScreens() {
        assertTrue(presenceEligible(true, false, Screen.Tutor, 45_000, 0))
        assertFalse(presenceEligible(true, false, Screen.Tutor, 45_001, 0))
        assertFalse(presenceEligible(false, false, Screen.Tutor, 5_000, 0))
        assertFalse(presenceEligible(true, true, Screen.Tutor, 5_000, 0))
        assertFalse(presenceEligible(true, false, Screen.ParentDashboard, 5_000, 0))
        assertFalse(presenceEligible(true, false, Screen.Mastery, 5_000, 0))
        assertFalse(presenceEligible(true, false, Screen.Tutor, 0, 5_000))
    }
}
