package com.konetibalaji.learning

data class DocumentPreview(val documentId: String, val chapterId: String, val title: String,
    val page: Int, val totalPages: Int, val start: Int, val end: Int, val text: String)

fun validateDocumentPreview(preview: DocumentPreview, documentId: String, chapterId: String, page: Int): DocumentPreview {
    require(preview.documentId == documentId && preview.chapterId == chapterId && preview.page == page)
    require(preview.totalPages > 0 && page in 0 until preview.totalPages)
    require(preview.start >= 0 && preview.end > preview.start)
    val characters = preview.text.codePointCount(0, preview.text.length)
    require(characters in 1..2000 && preview.end.toLong() - preview.start == characters.toLong())
    return preview
}
