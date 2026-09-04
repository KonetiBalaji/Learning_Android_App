package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Test

class ApiTimeoutTest {
    @Test fun reviewedGenerationHasBoundedExtraTimeWithoutSlowingOrdinaryReads() {
        assertEquals(135_000, apiReadTimeout("POST", "/v1/mastery/diagnostics"))
        assertEquals(135_000, apiReadTimeout("POST", "/v1/documents/id/quizzes"))
        assertEquals(135_000, apiReadTimeout("POST", "/v1/mastery/sessions/id/practice"))
        assertEquals(135_000, apiReadTimeout("POST", "/v1/mastery/sessions/id/rewrite"))
        assertEquals(30_000, apiReadTimeout("GET", "/v1/mastery/diagnostics"))
        assertEquals(30_000, apiReadTimeout("POST", "/v1/auth/login"))
        assertEquals(30_000, apiReadTimeout("POST", "/v1/documents"))
    }
}
