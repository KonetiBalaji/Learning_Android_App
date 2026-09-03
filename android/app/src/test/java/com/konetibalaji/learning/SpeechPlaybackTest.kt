package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class SpeechPlaybackTest {
    @Test fun finishRequiresEveryChunkAndIgnoresDuplicateCallbacks() {
        val queue = SpeechPlayback()
        val ids = queue.begin(2)
        assertFalse(queue.complete(ids[1]))
        assertFalse(queue.complete(ids[1]))
        assertTrue(queue.active)
        assertTrue(queue.complete(ids[0]))
        assertFalse(queue.active)
    }

    @Test fun stoppedPlaybackCannotAffectRestartedPlayback() {
        val queue = SpeechPlayback()
        val old = queue.begin(1).single()
        assertTrue(queue.stop())
        val current = queue.begin(1).single()
        assertNotEquals(old, current)
        assertFalse(queue.complete(old))
        assertFalse(queue.fail(old))
        assertTrue(queue.active)
        assertTrue(queue.complete(current))
    }

    @Test fun errorInvalidatesRemainingChunksAndStopIsIdempotent() {
        val queue = SpeechPlayback()
        val ids = queue.begin(2)
        assertFalse(queue.fail(null))
        assertTrue(queue.fail(ids[0]))
        assertFalse(queue.active)
        assertFalse(queue.complete(ids[1]))
        assertFalse(queue.stop())
    }

    @Test(expected = IllegalArgumentException::class)
    fun emptyPlaybackIsRejected() { SpeechPlayback().begin(0) }
}
