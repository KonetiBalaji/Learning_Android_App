package com.konetibalaji.learning

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
