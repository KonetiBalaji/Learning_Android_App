package com.konetibalaji.learning

/** Remove only the selected material; other current learning must be preserved. */
fun stateAfterDocumentDeletion(state: AppUiState, documentId: String): AppUiState {
    val updated = state.copy(documentLibrary = state.documentLibrary?.filterNot { it.id == documentId })
    return if (state.document?.id == documentId) updated.copy(
        document = null, selectedChapterIds = emptySet(), quizId = null, question = null, savedQuizDifficulty = null,
        feedback = null, results = null, canResumeDocumentQuiz = false,
    ) else updated
}
