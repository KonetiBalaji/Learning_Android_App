package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class GoogleSessionTest {
    @Test fun passwordRejectionKeepsSafeAuthErrorAndDoesNotPersist() {
        val rejected = apiFailure(401, authenticationRequest = true)
        var persisted = false
        var rolledBack = false
        val caught = assertThrows(ApiFailure::class.java) {
            establishVerifiedSession<String>({ throw rejected }, { persisted = true }, { rolledBack = true })
        }
        assertSame(rejected, caught)
        assertFalse(caught.sessionExpired)
        assertFalse(persisted)
        assertTrue(rolledBack)
    }

    @Test fun persistsOnlyServerVerifiedIdentity() {
        val events = mutableListOf<String>()
        val email = establishVerifiedSession(
            { events.add("verify"); "stored@example.test" },
            { events.add("save:$it") }, { events.add("rollback") },
        )
        assertEquals("stored@example.test", email)
        assertEquals(listOf("verify", "save:stored@example.test"), events)
    }

    @Test fun profileFailureNeverPersistsAndRollsBackProvisionalToken() {
        var persisted = false
        var rolledBack = false
        assertThrows(IllegalStateException::class.java) {
            establishVerifiedSession<String>(
                { error("profile unavailable") }, { persisted = true }, { rolledBack = true },
            )
        }
        assertFalse(persisted)
        assertTrue(rolledBack)
    }

    @Test fun secureStorageFailureRollsBack() {
        var rolledBack = false
        assertThrows(IllegalStateException::class.java) {
            establishVerifiedSession({ "stored@example.test" }, { error("storage failure") }, { rolledBack = true })
        }
        assertTrue(rolledBack)
    }

    @Test fun rollbackFailureDoesNotExposeExceptionDetails() {
        val failure = assertThrows(ApiFailure::class.java) {
            establishVerifiedSession<String>({ error("private details") }, {}, { error("more private details") })
        }
        assertTrue(failure.message!!.contains("could not be cleared"))
        assertFalse(failure.message!!.contains("private details"))
    }

    @Test fun cancellationAlsoRollsBack() {
        var rolledBack = false
        assertThrows(java.util.concurrent.CancellationException::class.java) {
            establishVerifiedSession<String>({ throw java.util.concurrent.CancellationException() }, {}, { rolledBack = true })
        }
        assertTrue(rolledBack)
    }

    @Test fun googleErrorsDoNotClaimPasswordFailureOrAutomaticLinking() {
        assertFalse(googleExchangeFailure(401).sessionExpired)
        assertFalse(googleExchangeFailure(401).message!!.contains("password"))
        assertTrue(googleExchangeFailure(409).message!!.contains("not linked automatically"))
        assertEquals(apiFailure(503, true).message, googleExchangeFailure(503).message)
    }

    @Test fun googleChallengeRequiresBoundedBase64UrlNonceAndLifetime() {
        val nonce = "a".repeat(42) + "-"
        assertEquals(nonce, validateGoogleChallenge(nonce, 300))
        for (invalid in listOf("a".repeat(42), "a".repeat(129), "a".repeat(42) + "+")) {
            assertThrows(IllegalArgumentException::class.java) { validateGoogleChallenge(invalid, 300) }
        }
        assertThrows(IllegalArgumentException::class.java) { validateGoogleChallenge(nonce, 0) }
        assertThrows(IllegalArgumentException::class.java) { validateGoogleChallenge(nonce, 301) }
    }
}
