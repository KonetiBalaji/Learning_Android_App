package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class TutorPresenceTest {
    @Test fun ready_when_idle() = assertEquals(TutorPresence.READY, tutorPresence(loading = false, reading = false))
    @Test fun speaking_follows_real_playback() = assertEquals(TutorPresence.SPEAKING, tutorPresence(loading = false, reading = true))
    @Test fun thinking_takes_priority_during_request() = assertEquals(TutorPresence.THINKING, tutorPresence(loading = true, reading = true))
}
