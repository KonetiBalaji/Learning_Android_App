package com.konetibalaji.learning

import java.net.HttpURLConnection

/** Server response bodies are deliberately excluded: validation details may echo passwords. */
class ApiFailure(val status: Int, val sessionExpired: Boolean, message: String) : Exception(message)

fun apiFailure(status: Int, authenticationRequest: Boolean = false, recoveryCode: String? = null): ApiFailure {
    val expired = status == 401 && !authenticationRequest
    val message = when {
        expired -> "Your session has expired or is no longer valid. Please sign in again."
        status == 401 -> "Email or password is incorrect. Please try again."
        status == 403 -> "You do not have access to this learning material."
        status == 404 -> "This saved learning item is no longer available."
        status == 409 && authenticationRequest -> "This account already exists. Please sign in."
        status == 409 -> "This activity has changed. Resume saved learning before trying again."
        status == 413 -> "The selected file is too large. Choose a file under 50 MB."
        status == 415 -> "This file type is not supported. Choose PDF, DOCX or plain text."
        status == 422 -> (if (authenticationRequest) null else documentRecoveryMessage(recoveryCode))
            ?: "Please check your input or selected document and try again."
        status == 429 -> "Too many requests. Please wait a moment before trying again."
        status >= 500 -> "The learning service is temporarily unavailable. Please try again."
        else -> "The request could not be completed. Please try again."
    }
    return ApiFailure(status, expired, message)
}

/** Only exact known codes select client-owned text; never interpolate headers or bodies. */
private fun documentRecoveryMessage(code: String?): String? = when (code) {
    "insufficient_quiz_material" -> "This selection cannot support that many distinct questions. Choose fewer questions or select more source text. Your selection is unchanged."
    "empty_pdf_pages" -> "These PDF pages have no extracted text. Choose pages with text; scanned pages need OCR, which is not available. Your selection is unchanged."
    "pdf_coverage_gap" -> "Some text on these pages is missing from the chapter structure. Use Check for omitted text, then load and review the PDF pages again. Your selection is unchanged."
    "too_many_pdf_ranges" -> "These pages span more than 50 source ranges. Choose fewer PDF pages and review again. Your selection is unchanged."
    "document_count_limit" -> "You reached the saved-document limit. Delete a document from My uploaded documents, then try again."
    "document_bytes_limit" -> "Your saved documents use the available storage. Delete documents you no longer need, then try again."
    else -> null
}

/** Closes all response streams and the connection, including malformed/non-JSON errors. */
fun readApiResponse(connection: HttpURLConnection, authenticationRequest: Boolean = false): String {
    try {
        val status = connection.responseCode
        if (status !in 200..299) {
            val recoveryCode = if (status == 422 && !authenticationRequest)
                runCatching { connection.getHeaderField("X-Learning-Error") }.getOrNull() else null
            runCatching { connection.errorStream?.close() }
            throw apiFailure(status, authenticationRequest, recoveryCode)
        }
        if (status == 204) return ""
        return connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
    } finally {
        connection.disconnect()
    }
}
