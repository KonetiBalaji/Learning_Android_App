package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class GuardianAccessHistoryTest {
    @Test
    fun descriptionsAreLearnerOwnedAndExplicit() {
        assertEquals("Report access granted", guardianAccessEventDescription("granted"))
        assertEquals("You revoked report access", guardianAccessEventDescription("revoked_by_learner"))
        assertEquals("Parent or teacher removed access", guardianAccessEventDescription("revoked_by_guardian"))
        assertEquals("Report access changed", guardianAccessEventDescription("future_event"))
    }

    @Test
    fun deletedGuardianIdentityIsNeverInvented() {
        val deleted = GuardianAccessEvent("event", null, null, "revoked_by_guardian", "2026-09-05T00:00:00Z")
        val active = deleted.copy(guardianId = "guardian", guardianEmail = "guardian@example.com")
        assertEquals("Deleted account", guardianAccessAccountLabel(deleted))
        assertEquals("guardian@example.com", guardianAccessAccountLabel(active))
    }

    @Test
    fun timestampIsReadableAndMalformedValuesFailClosed() {
        assertEquals("Sep 4, 2026 · 11:32 AM", guardianAccessOccurredLabel("2026-09-04T11:32:55.708518+00:00"))
        assertEquals("Time unavailable", guardianAccessOccurredLabel("not-a-time"))
    }
}
