package com.konetibalaji.learning

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream

class DocumentUploadTest {
    @Test fun uncertainUploadDirectsToLibraryBeforeRetry() {
        val message = uncertainUploadFailure().message!!
        assertTrue(message.contains("Check My uploaded documents before trying again"))
        assertTrue(message.contains("may already be saved"))
    }
    @Test fun exactLimitIsAccepted() {
        val output = ByteArrayOutputStream()
        assertEquals(8L, copyDocument(ByteArrayInputStream(ByteArray(8) { 3 }), output, 8))
        assertArrayEquals(ByteArray(8) { 3 }, output.toByteArray())
    }

    @Test fun unknownOrFalseSizeCannotBypassStreamLimit() {
        validateDocumentSize(null)
        validateDocumentSize(-1)
        validateDocumentSize(1)
        val output = ByteArrayOutputStream()
        assertThrows(DocumentUploadException::class.java) { copyDocument(ByteArrayInputStream(ByteArray(9)), output, 8) }
        assertTrue(output.size() <= 8)
    }

    @Test fun rejectsEmptyAndOversizeMetadata() {
        assertThrows(DocumentUploadException::class.java) { validateDocumentSize(MAX_DOCUMENT_BYTES + 1) }
        assertThrows(DocumentUploadException::class.java) { validateDocumentSize(0) }
        assertThrows(DocumentUploadException::class.java) { copyDocument(ByteArrayInputStream(byteArrayOf()), ByteArrayOutputStream()) }
        validateDocumentSize(MAX_DOCUMENT_BYTES)
    }

    @Test fun neverReadsMoreThanOneBytePastLimit() {
        var read = 0
        val infinite = object : InputStream() { override fun read(): Int { read++; return 7 } }
        assertThrows(DocumentUploadException::class.java) { copyDocument(infinite, ByteArrayOutputStream(), 20) }
        assertEquals(21, read)
    }

    @Test fun headersCannotContainNewlinesQuotesOrPaths() {
        val name = safeDocumentName("C:\\private\\notes\r\n\".txt")
        assertEquals("notes.txt", name)
        assertEquals("text/plain", documentMediaType(name))
        assertEquals("application/pdf", documentMediaType("NOTES.PDF"))
        assertThrows(DocumentUploadException::class.java) { documentMediaType("notes.exe") }
    }
}
