package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class LearningBadgesTest {
    @Test fun supportedServerBadgeIsAccepted() {
        val value = LearningBadge("learn_from_mistakes", "Learn from mistakes",
            "Corrected an independently missed concept in a rewrite.", "2026-09-04T12:00:00+00:00")
        assertEquals(value, validateLearningBadge(value))
    }

    @Test fun inventedOrMalformedBadgeFailsClosed() {
        val valid = LearningBadge("first_answer", "First answer", "Completed the first diagnostic answer.", "2026-09-04")
        assertThrows(IllegalArgumentException::class.java) { validateLearningBadge(valid.copy(id = "winner")) }
        assertThrows(IllegalArgumentException::class.java) { validateLearningBadge(valid.copy(description = " ")) }
        assertThrows(IllegalArgumentException::class.java) { validateLearningBadge(valid.copy(earnedAt = "")) }
    }
}
