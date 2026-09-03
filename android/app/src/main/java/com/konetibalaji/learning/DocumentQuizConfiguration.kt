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
