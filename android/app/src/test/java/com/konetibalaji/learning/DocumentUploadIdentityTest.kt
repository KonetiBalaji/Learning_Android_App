package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test

class DocumentUploadIdentityTest {
    private val first = "12345678-1234-4234-8234-123456789012"
    private val second = "87654321-1234-4234-8234-123456789012"

    @Test fun sameSelectionReusesSavedIdentityAcrossReconstruction() {
        var disk: String? = null
        val fingerprint = documentUploadSelectionFingerprint(DocumentUploadSelection("cells.txt", 1234))
        assertEquals(first, prepareDocumentUpload(disk, fingerprint, { disk = it; true }, { first }))
        assertEquals(first, prepareDocumentUpload(disk, fingerprint, { disk = it; true }, { error("new id") }))
    }

    @Test fun aDifferentSelectionGetsANewIdentity() {
        val old = documentUploadSelectionFingerprint(DocumentUploadSelection("old.txt", 1234))
        val changed = documentUploadSelectionFingerprint(DocumentUploadSelection("new.txt", 1234))
        assertNotEquals(old, changed)
        assertEquals(second, prepareDocumentUpload("$first|$old", changed, { true }, { second }))
    }

    @Test fun invalidOrUnpersistedIdentityFailsClosed() {
        val fingerprint = documentUploadSelectionFingerprint(DocumentUploadSelection("selection.txt", null))
        assertThrows(IllegalStateException::class.java) {
            prepareDocumentUpload(null, fingerprint, { false }, { first })
        }
        listOf("broken", "$first|bad", "bad-uuid|$fingerprint").forEach { saved ->
            assertThrows(IllegalArgumentException::class.java) {
                prepareDocumentUpload(saved, fingerprint, { error("overwrite") }, { error("new id") })
            }
        }
    }
}
