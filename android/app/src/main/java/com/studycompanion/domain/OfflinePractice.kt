package com.studycompanion.domain

import kotlin.random.Random

data class OfflinePassage(val id: String, val sectionId: String, val page: Int, val text: String)
data class OfflineQuestion(val id: String, val prompt: String, val choices: List<String>, val answer: Int,
    val type: String, val source: OfflinePassage, val explanation: String)

/** Easy exact-passage recall only. Never claims semantic reasoning or invents source text. */
object OfflinePractice {
    private val words = Regex("\\b[A-Za-z][A-Za-z-]{4,}\\b")

    fun generate(passages: List<OfflinePassage>, count: Int, kind: String, random: Random = Random.Default): List<OfflineQuestion> {
        require(count in 1..50) { "Choose between 1 and 50 questions." }
        require(kind in listOf("multiple_choice", "true_false", "yes_no")) { "Choose a supported question type." }
        val pool = passages.flatMap { words.findAll(it.text).map { match -> match.value.lowercase() }.toList() }.distinct()
        val candidates = passages.filter { it.text.trim().split(Regex("\\s+")).size >= 7 && words.containsMatchIn(it.text) }
            .distinctBy { it.text.lowercase() }.shuffled(random)
        val questions = candidates.mapNotNull { passage ->
            val word = words.findAll(passage.text).maxBy { it.value.length }
            val others = pool.filter { !it.equals(word.value, ignoreCase = true) }
            if (others.size < 3) return@mapNotNull null
            val quote = passage.text
            val prompt: String
            val choices: List<String>
            val answer: Int
            if (kind == "multiple_choice") {
                choices = (listOf(word.value) + others.shuffled(random).take(3)).shuffled(random)
                answer = choices.indexOf(word.value)
                prompt = "Which word completes this exact passage?\n“" + quote.replaceRange(word.range, "_____") + "”"
            } else {
                val positive = random.nextBoolean()
                val shown = if (positive) quote else quote.replaceRange(word.range, others.random(random))
                choices = if (kind == "yes_no") listOf("Yes", "No") else listOf("True", "False")
                answer = if (positive) 0 else 1
                prompt = (if (kind == "yes_no") "Does this exactly match the source passage?\n“" else "True or false: this exactly matches the source passage.\n“") + shown + "”"
            }
            OfflineQuestion("q0", prompt, choices, answer, kind, passage,
                "The original passage says: “$quote” Read it again and connect the missing word to its context.")
        }.take(count).mapIndexed { index, question -> question.copy(id = "q$index") }
        require(questions.size == count) { "This selection supports ${questions.size} distinct local questions. Choose fewer questions or more material." }
        return questions
    }
}
