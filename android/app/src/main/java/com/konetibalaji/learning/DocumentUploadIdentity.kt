package com.konetibalaji.learning

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import java.security.MessageDigest
import java.util.UUID

data class DocumentUploadSelection(val originalName: String, val declaredSize: Long?)

fun documentUploadSelection(resolver: ContentResolver, uri: Uri): DocumentUploadSelection {
    var name = "study-material.txt"
    var size: Long? = null
    resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) {
            val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (nameIndex >= 0 && !cursor.isNull(nameIndex)) name = cursor.getString(nameIndex)
            if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex)
        }
    }
    return DocumentUploadSelection(safeDocumentName(name), size)
}

fun documentUploadSelectionFingerprint(selection: DocumentUploadSelection): String {
    val canonical = listOf(selection.originalName, selection.declaredSize?.toString() ?: "unknown")
        .joinToString("") { "${it.length}:$it" }
    val bytes = canonical.toByteArray(Charsets.UTF_8)
    return MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
}

fun prepareDocumentUpload(
    saved: String?, selectionFingerprint: String, persist: (String) -> Boolean,
    newId: () -> String = { UUID.randomUUID().toString() },
): String {
    require(selectionFingerprint.matches(Regex("[0-9a-f]{64}"))) { "Upload selection identity is invalid" }
    val previous = saved?.split('|')
    if (previous != null) {
        require(previous.size == 2 && previous[1].matches(Regex("[0-9a-f]{64}")) &&
            runCatching { UUID.fromString(previous[0]).toString() == previous[0] }.getOrDefault(false)) {
            "Saved upload request identity is invalid"
        }
    }
    val id = if (previous != null && previous[1] == selectionFingerprint) previous[0] else newId()
    check(persist("$id|$selectionFingerprint")) { "Could not save upload request before submission" }
    return id
}
