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

fun nextDocumentDifficulty(value: String?): String? = when (restoredDocumentDifficulty(value)) {
    "easy" -> "medium"
    "medium" -> "hard"
    else -> null
}

val documentQuestionTypes = linkedMapOf(
    "multiple_choice" to "Multiple choice",
    "true_false" to "True / False",
    "yes_no" to "Yes / No",
)

fun restoredDocumentQuestionType(value: String?): String =
    value?.takeIf { it in documentQuestionTypes } ?: "multiple_choice"

fun documentQuestionTypeLabel(value: String?): String =
    documentQuestionTypes[value]?.let { "Question type: $it" } ?: "Question type: unspecified"

fun validateDocumentFormat(requested: String, returned: String?) {
    require(requested in documentQuestionTypes) { "Unsupported requested quiz format" }
    require(returned == requested || (returned == null && requested == "multiple_choice")) {
        "Server did not confirm the requested quiz format"
    }
}

fun validateDocumentOptions(type: String?, options: List<String>) {
    val valid = when (type) {
        null, "multiple_choice" -> options.size == 4 && options.all { it.isNotBlank() } &&
            options.map { it.trim().lowercase(java.util.Locale.ROOT) }.distinct().size == 4
        "true_false" -> options == listOf("True", "False")
        "yes_no" -> options == listOf("Yes", "No")
        else -> false
    }
    require(valid) { "Invalid answer choices for the quiz format" }
}
