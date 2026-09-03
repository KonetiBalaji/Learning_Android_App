package com.konetibalaji.learning

import java.io.InputStream
import java.io.OutputStream

const val MAX_DOCUMENT_BYTES = 50L * 1024 * 1024
class DocumentUploadException(message: String) : Exception(message)

fun validateDocumentSize(size: Long?) {
    if (size != null && size > MAX_DOCUMENT_BYTES) throw DocumentUploadException("The selected file is too large. Choose a file up to 50 MB.")
    if (size == 0L) throw DocumentUploadException("The selected file is empty. Choose a document with learning material.")
}

/** Bounded buffers and a one-byte over-limit probe; never materializes the whole document. */
fun copyDocument(input: InputStream, output: OutputStream, limit: Long = MAX_DOCUMENT_BYTES, onProgress: (Long) -> Unit = {}): Long {
    require(limit > 0)
    val buffer = ByteArray(16 * 1024)
    var total = 0L
    while (true) {
        val count = input.read(buffer, 0, minOf(buffer.size.toLong(), limit - total + 1).toInt())
        if (count < 0) break
        if (count == 0) {
            val single = input.read()
            if (single < 0) break
            if (total == limit) throw DocumentUploadException("The selected file is too large. Choose a file up to 50 MB.")
            output.write(single)
            total++
            onProgress(total)
            continue
        }
        if (total + count > limit) throw DocumentUploadException("The selected file is too large. Choose a file up to 50 MB.")
        output.write(buffer, 0, count)
        total += count
        onProgress(total)
    }
    if (total == 0L) throw DocumentUploadException("The selected file is empty. Choose a document with learning material.")
    return total
}

fun safeDocumentName(name: String): String = name.substringAfterLast('/').substringAfterLast('\\')
    .filter { it >= ' ' && it != '\u007f' && it != '"' }.takeLast(180).ifBlank { "study-material.txt" }

fun documentMediaType(name: String): String = when (name.substringAfterLast('.', "").lowercase()) {
    "pdf" -> "application/pdf"
    "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    "txt" -> "text/plain"
    else -> throw DocumentUploadException("This file type is not supported. Choose PDF, DOCX or plain text.")
}
