package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class MasterySubmissionStateTest {
    @Test fun decodingFailureDoesNotAcknowledgeNewState() {
        val state = MasterySubmissionState()
        state.remember("a", "old")
        assertThrows(IllegalStateException::class.java) {
            state.accept("a", "new") { error("Malformed response") }
        }
        assertEquals("old", state.expected("a"))
        val result = state.accept("a", "new") { "decoded" }
        assertEquals("decoded", result)
        assertEquals("new", state.expected("a"))
    }

    @Test fun failedFirstDecodeDoesNotCreateSubmissionState() {
        val state = MasterySubmissionState()
        assertThrows(IllegalStateException::class.java) {
            state.accept("a", "new") { error("Malformed start or resume") }
        }
        assertThrows(IllegalArgumentException::class.java) { state.expected("a") }
    }
    @Test fun failedRequestsRetainOldStateUntilSuccessfulResponseOrResume() {
        val state = MasterySubmissionState()
        state.remember("a", "a:diagnostic:0")
        assertEquals("a:diagnostic:0", state.expected("a"))
        assertThrows(IllegalArgumentException::class.java) { state.remember("a", "") }
        assertEquals("a:diagnostic:0", state.expected("a"))
        state.remember("a", "a:diagnostic:1")
        assertEquals("a:diagnostic:1", state.expected("a"))
    }

    @Test fun sessionsAreIsolatedAndSignOutClearsState() {
        val state = MasterySubmissionState()
        state.remember("a", "one")
        state.remember("b", "two")
        assertEquals("one", state.expected("a"))
        assertEquals("two", state.expected("b"))
        state.clear()
        assertThrows(IllegalArgumentException::class.java) { state.expected("a") }
        assertThrows(IllegalArgumentException::class.java) { state.expected("b") }
    }
}
