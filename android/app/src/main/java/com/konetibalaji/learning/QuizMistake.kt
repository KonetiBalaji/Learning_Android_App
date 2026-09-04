package com.konetibalaji.learning

import java.util.UUID

data class QuizMistake(
    val question: QuizQuestion,
    val selectedOption: String,
    val correctOption: String,
    val explanation: String,
)

fun validateQuizMistake(value: QuizMistake): QuizMistake {
    require(value.question.prompt.isNotBlank() && value.question.sourceReference.isNotBlank())
    require(value.selectedOption in value.question.options)
    require(value.correctOption in value.question.options)
    require(value.selectedOption != value.correctOption)
    require(value.explanation.isNotBlank())
    return value
}

fun prepareMistakeRetry(saved: String?, persist: (String) -> Boolean,
                        newId: () -> String = { UUID.randomUUID().toString() }): String {
    if (saved != null) require(runCatching { UUID.fromString(saved).toString() == saved }.getOrDefault(false)) {
        "Saved mistake retry identity is invalid"
    }
    val id = saved ?: newId()
    check(persist(id)) { "Could not save retry request" }
    return id
}
