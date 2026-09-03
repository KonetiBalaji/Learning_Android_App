package com.konetibalaji.learning

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.OutputStream
import org.junit.Assert.*
import org.junit.Test

class DocumentUploadProgressTest {
    @Test fun knownSizeIsAnEstimateAndNeverClaimsCompletion() {
        assertEquals(0.5f, DocumentUploadProgress(512, 1024).fraction!!, 0.001f)
        assertEquals(0.99f, DocumentUploadProgress(1024, 1024).fraction!!, 0.001f)
        assertTrue(DocumentUploadProgress(512, 1024).detail.contains("estimated 50%"))
    }

    @Test fun unknownOrExceededMetadataDoesNotInventPercentage() {
        listOf(null, -1L, 0L, 100L).forEach {
            val progress = DocumentUploadProgress(200, it)
            assertNull(progress.fraction)
            assertFalse(progress.detail.contains("%"))
        }
    }

    @Test fun analysisWaitIsNotUploadOrQuizSuccess() {
        val progress = DocumentUploadProgress(100, 100, awaitingAnalysis = true)
        assertNull(progress.fraction)
        assertEquals("Waiting for document analysis…", progress.title)
        assertTrue(progress.detail.contains("Waiting for the service"))
        assertFalse(progress.detail.contains("100%"))
    }

    @Test fun progressFollowsOnlySuccessfullyWrittenBytes() {
        val written = ByteArrayOutputStream()
        val updates = mutableListOf<Long>()
        copyDocument(ByteArrayInputStream(ByteArray(40000)), written, onProgress = {
            assertEquals(written.size().toLong(), it)
            updates.add(it)
        })
        assertEquals(listOf(16384L, 32768L, 40000L), updates)
        val failed = object : OutputStream() { override fun write(value: Int) { throw IOException("failure") } }
        var reported = false
        assertThrows(IOException::class.java) {
            copyDocument(ByteArrayInputStream(byteArrayOf(1)), failed, onProgress = { reported = true })
        }
        assertFalse(reported)
    }

    @Test fun invalidProgressRejected() {
        assertThrows(IllegalArgumentException::class.java) { DocumentUploadProgress(-1) }
        assertThrows(IllegalArgumentException::class.java) { DocumentUploadProgress(MAX_DOCUMENT_BYTES + 1) }
    }
}
