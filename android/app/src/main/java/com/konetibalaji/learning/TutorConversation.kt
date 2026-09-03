package com.konetibalaji.learning

data class TutorChatTurn(val requestId: String, val question: String, val status: String,
                         val answer: String?, val supported: Boolean?) {
    init {
        require(requestId.isNotBlank() && question.isNotBlank())
        require(status in setOf("pending", "complete", "failed"))
        require(if (status == "complete") !answer.isNullOrBlank() && supported != null else answer == null && supported == null)
    }
}

data class PendingTutorQuestion(val requestId: String, val question: String)

fun pendingTutorQuestion(turns: List<TutorChatTurn>, uncertain: PendingTutorQuestion?): PendingTutorQuestion? {
    turns.lastOrNull { it.status == "pending" }?.let { return PendingTutorQuestion(it.requestId, it.question) }
    return uncertain?.takeUnless { pending -> turns.any { it.requestId == pending.requestId } }
}

fun boundedTutorQuestion(value: String): String = value.take(1000).let {
    if (it.lastOrNull()?.isHighSurrogate() == true) it.dropLast(1) else it
}

fun mergeTutorTurn(turns: List<TutorChatTurn>, turn: TutorChatTurn): List<TutorChatTurn> =
    if (turns.any { it.requestId == turn.requestId }) turns.map { if (it.requestId == turn.requestId) turn else it }
    else turns + turn
