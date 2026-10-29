package com.studycompanion.domain

object QuizRules {
    fun canSubmit(selected: Int?, feedbackVisible: Boolean, busy: Boolean): Boolean =
        selected != null && !feedbackVisible && !busy

    fun questionCount(input: String): Int? = input.toIntOrNull()?.takeIf { it in 1..50 }
}
