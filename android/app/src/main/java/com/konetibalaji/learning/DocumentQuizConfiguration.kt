package com.konetibalaji.learning

fun validDocumentQuestionCount(input: String): Int? =
    input.trim().toIntOrNull()?.takeIf { it in 5..20 }

val documentDifficulties = linkedMapOf(
    "easy" to "Easy · recall a fact",
    "medium" to "Medium · apply a principle",
    "hard" to "Hard · combine facts",
    "mixed" to "Mixed · varied reasoning",
)

fun restoredDocumentDifficulty(value: String?): String = value?.takeIf { it in documentDifficulties } ?: "easy"
fun requestedDifficultyLabel(value: String?): String =
    documentDifficulties[value]?.let { "Requested difficulty: $it" } ?: "Requested difficulty: unspecified"

val documentQuestionTypes = linkedMapOf(
    "multiple_choice" to "Multiple choice",
    "true_false" to "True / False",
    "yes_no" to "Yes / No",
)

fun restoredDocumentQuestionType(value: String?): String =
    value?.takeIf { it in documentQuestionTypes } ?: "multiple_choice"

fun documentQuestionTypeLabel(value: String?): String =
    documentQuestionTypes[value]?.let { "Question type: $it" } ?: "Question type: unspecified"
