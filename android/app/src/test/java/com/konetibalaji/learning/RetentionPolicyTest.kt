package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class RetentionPolicyTest {
    private val valid = RetentionPolicy("until_account_deletion",
        "until_document_or_account_deletion", "queued_for_immediate_cleanup", 30, 24, 30)

    @Test fun knownPolicyIsAccepted() {
        assertEquals(valid, validateRetentionPolicy(valid))
    }

    @Test fun unknownOrUnsafePolicyFailsClosed() {
        assertThrows(IllegalArgumentException::class.java) {
            validateRetentionPolicy(valid.copy(activeLearningData = "forever"))
        }
        assertThrows(IllegalArgumentException::class.java) {
            validateRetentionPolicy(valid.copy(backupDays = 0))
        }
    }
}
