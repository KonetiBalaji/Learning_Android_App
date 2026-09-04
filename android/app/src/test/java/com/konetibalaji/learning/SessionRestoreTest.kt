package com.konetibalaji.learning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SessionRestoreTest {
    @Test fun cleanSignedOutStateHasNoRecoveryError() {
        assertNull(sessionRestoreError(readOperationFailed = false, encryptedReadFailed = false))
    }

    @Test fun storageOrAuthenticatedDecryptionFailureIsVisible() {
        assertEquals(SESSION_RESTORE_ERROR, sessionRestoreError(true, false))
        assertEquals(SESSION_RESTORE_ERROR, sessionRestoreError(false, true))
    }
}
