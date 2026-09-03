package com.konetibalaji.learning

enum class SubmittedFlow { MASTERY, DOCUMENT }

/** Only mutations opt into recovery. Resume requests never recursively resume. */
fun recoveryAfterFailure(status: Int?, submittedFlow: SubmittedFlow?): SubmittedFlow? =
    submittedFlow.takeIf { status == 409 }

/** Explicit server-to-screen contract. Unknown states must not silently award mastery. */
fun screenForMasteryStatus(status: String): Screen = when (status) {
    "diagnostic" -> Screen.Diagnostic
    "tutor" -> Screen.Tutor
    "practice" -> Screen.Practice
    "rewrite" -> Screen.Rewrite
    "mastered" -> Screen.Mastery
    else -> error("The saved learning phase is not supported.")
}

fun screenForLearningAction(action: String): Screen = when (action) {
    "next_question" -> Screen.Diagnostic
    "tutor" -> Screen.Tutor
    "mastery" -> Screen.Mastery
    else -> error("The learning action is not supported.")
}
