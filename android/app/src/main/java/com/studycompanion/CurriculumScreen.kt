package com.studycompanion

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.studycompanion.data.strings

@Composable
fun CurriculumScreen(state: StudyState, model: StudyViewModel, onSpeakingChanged: (Boolean) -> Unit) {
    var grade by rememberSaveable { mutableStateOf<Int?>(null) }
    var subject by rememberSaveable { mutableStateOf<String?>(null) }
    state.readinessCheck?.let { check ->
        val full = check.getString("id") == "grade6-math-full"
        Text(if (full) "Full Grade 6 Mathematics readiness check" else "Grade 6 Mathematics readiness check",
            style = MaterialTheme.typography.headlineSmall)
        val total = check.getInt("total")
        if (check.getBoolean("complete")) {
            Text("${check.getInt("correct")} / $total correct", style = MaterialTheme.typography.titleLarge)
            ReadinessBreakdown(check.getJSONObject("by_chapter"))
            Text(if (full) "This score covers the five Grade 6 Mathematics starter chapters."
                else "This score covers this short fractions and decimals assessment.")
        } else {
            Text("Question ${check.getInt("index") + 1} of $total")
            Text(check.getString("prompt"))
            check.getJSONArray("choices").strings().forEachIndexed { index, choice ->
                CurriculumButton(choice, !state.busy) { model.answerReadiness(index) }
            }
        }
        CurriculumButton("Back to chapters", !state.busy, model::closeReadiness)
        return
    }
    val lesson = state.curriculumLesson
    if (lesson == null) {
        when {
            grade == null -> {
                Text("Select your grade", style = MaterialTheme.typography.headlineSmall)
                val badges = state.curriculumChapters.filter { it.getBoolean("mastered") }
                if (badges.isNotEmpty()) {
                    Text("Mastery badges", style = MaterialTheme.typography.titleMedium)
                    badges.forEach { Text(it.getString("title") + " badge earned") }
                }
                val grades = state.curriculumChapters.map { it.getInt("grade") }.toSet()
                for (number in 1..12) {
                    CurriculumButton("Grade $number" + if (number !in grades) " · no lessons yet" else "",
                        !state.busy && number in grades) { grade = number }
                }
            }
            subject == null -> {
                Text("Grade $grade · Select a subject", style = MaterialTheme.typography.headlineSmall)
                val chapters = state.curriculumChapters.filter { it.getInt("grade") == grade }
                val studiedSubjects = chapters.filter { it.getBoolean("mastered") }.map { it.getString("subject") }.toSet()
                val next = nextCurriculumChapter(chapters, studiedSubjects)
                if (next != null && (next.optBoolean("started") || studiedSubjects.isNotEmpty())) {
                    val name = next.getString("subject")
                    val action = when {
                        next.optBoolean("needs_practice") -> "Review"
                        next.optBoolean("started") -> "Continue"
                        else -> "Start next"
                    }
                    CurriculumButton("$action: ${next.getString("title")} · $name", !state.busy) {
                        subject = name
                        model.openCurriculumChapter(next.getString("id"))
                    }
                }
                chapters.map { it.getString("subject") }.distinct().forEach { name ->
                        CurriculumButton(name, !state.busy) { subject = name }
                    }
                CurriculumButton("Back to grades", !state.busy) { grade = null }
            }
            else -> {
                Text("$subject · Chapters", style = MaterialTheme.typography.headlineSmall)
                val chapters = state.curriculumChapters.filter { it.getInt("grade") == grade && it.getString("subject") == subject }
                val mastered = chapters.count { it.getBoolean("mastered") }
                Text("$mastered of ${chapters.size} chapters mastered")
                if (chapters.isNotEmpty()) {
                    LinearProgressIndicator(progress = { mastered.toFloat() / chapters.size }, modifier = Modifier.fillMaxWidth())
                }
                val next = nextCurriculumChapter(chapters)
                next?.let { Text("Suggested next: ${it.getString("title")}") }
                chapters.forEach { chapter ->
                        val label = when {
                            chapter.getBoolean("mastered") -> " · Mastered"
                            chapter.getBoolean("locked") -> " · Locked"
                            chapter.optBoolean("needs_practice") && chapter.optInt("review_events") >= 2 ->
                                " · Repeated difficulty"
                            chapter.optBoolean("needs_practice") -> " · Needs practice"
                            chapter.optBoolean("started") -> " · In progress"
                            else -> ""
                        }
                        CurriculumButton(chapter.getString("title") + label, !state.busy && !chapter.getBoolean("locked")) {
                            model.openCurriculumChapter(chapter.getString("id"))
                        }
                    }
                if (grade == 6 && subject == "Mathematics") {
                    val ready = setOf("fractions", "decimals").all { id ->
                        chapters.any { it.getString("id") == id && it.getBoolean("mastered") }
                    }
                    if (!ready) Text("Master fractions and decimals to unlock the readiness check.")
                    CurriculumButton("Open readiness check", !state.busy && ready) { model.openReadiness() }
                    val fullReady = setOf("fractions", "decimals", "percentages", "grade6-algebra", "grade6-geometry")
                        .all { id -> chapters.any { it.getString("id") == id && it.getBoolean("mastered") } }
                    if (!fullReady) Text("Master all five chapters to unlock the full readiness check.")
                    CurriculumButton("Open full readiness check", !state.busy && fullReady) {
                        model.openReadiness("grade6-math-full")
                    }
                }
                CurriculumButton("Back to subjects", !state.busy) { subject = null }
            }
        }
        return
    }

    val chapter = state.curriculumChapters.firstOrNull { it.getString("id") == lesson.getString("chapter_id") }
    Text(chapter?.getString("title").orEmpty(), style = MaterialTheme.typography.headlineSmall)
    lesson.getString("feedback").takeIf(String::isNotEmpty)?.let { Text(it) }
    val phase = lesson.getString("phase")
    val version = lesson.getInt("version")
    var response by rememberSaveable(lesson.getString("chapter_id"), version) { mutableStateOf("") }
    var hint by rememberSaveable(lesson.getString("chapter_id"), version) { mutableStateOf(false) }
    when (phase) {
        "diagnostic" -> {
            val number = lesson.optInt("diagnostic_index") + 1
            val total = lesson.optInt("diagnostic_total", 1)
            Text("Diagnostic question $number of $total", style = MaterialTheme.typography.titleMedium)
            Text(lesson.getString("prompt"))
            lesson.getJSONArray("choices").strings().forEachIndexed { choice, label ->
                CurriculumButton(label, !state.busy) { model.answerCurriculum("diagnostic", choice = choice) }
            }
        }
        "coach" -> {
            Text("Worked example", style = MaterialTheme.typography.titleMedium)
            val explanation = lesson.getString("explanation")
            val example = lesson.getString("example")
            val steps = lesson.optJSONArray("example_steps")?.strings().orEmpty()
            val variants = lesson.optJSONObject("example_variants")
            val chapterId = lesson.getString("chapter_id")
            var showExample by rememberSaveable(chapterId, version) { mutableStateOf(false) }
            var theme by rememberSaveable(chapterId, version) { mutableStateOf<String?>(null) }
            var index by rememberSaveable(chapterId, version) { mutableStateOf(0) }
            val themedExample = theme?.let { variants?.optString(it) }?.takeIf(String::isNotBlank)
            val narration = if (showExample) themedExample ?: steps.getOrNull(index) ?: example else explanation
            Text(explanation)
            ReadAloudButton(
                narration,
                if (showExample) "Read current example aloud" else "Read explanation aloud",
                onSpeakingChanged,
            )
            CurriculumButton(if (showExample) "Hide example steps" else "Show example steps", !state.busy) {
                if (showExample) {
                    theme = null
                    index = 0
                }
                showExample = !showExample
            }
            AnimatedVisibility(showExample) {
                Column {
                    if (variants != null) {
                        Text("Choose an example theme")
                        for (option in listOf("Soccer", "Gaming")) {
                            if (variants.has(option)) CurriculumButton("$option example", !state.busy) { theme = option }
                        }
                        if (themedExample != null) {
                            Text(themedExample)
                            CurriculumButton("Clear example theme", !state.busy) { theme = null }
                        }
                    }
                    Text(example)
                    if (steps.isNotEmpty()) {
                        Text("Step ${index + 1} of ${steps.size}")
                        Crossfade(targetState = index, label = "Worked example step") { step ->
                            Text(steps[step])
                        }
                        if (index > 0) CurriculumButton("Previous example step", !state.busy) { index-- }
                        if (index < steps.lastIndex) CurriculumButton("Next example step", !state.busy) { index++ }
                    }
                }
            }
            CurriculumButton(if (lesson.optBoolean("diagnostic_remaining")) "Next diagnostic question" else "Try a practice question",
                !state.busy) { model.answerCurriculum("continue") }
        }
        "practice", "rewrite" -> {
            Text(lesson.getString("prompt"))
            if (phase == "practice") {
                CurriculumButton("Show hint", !state.busy) { hint = true }
                if (hint) Text(lesson.getString("hint"))
            }
            OutlinedTextField(response, { if (it.length <= 1000) response = it }, modifier = Modifier.fillMaxWidth(),
                enabled = !state.busy, label = { Text(if (phase == "practice") "Your answer" else "Explain in your own words") })
            if (phase == "rewrite") DictateButton(!state.busy) { response = it.take(1000) }
            Button(onClick = { model.answerCurriculum(phase, response = response) }, enabled = !state.busy && response.isNotBlank()) {
                Text(if (phase == "practice") "Check answer" else "Check explanation")
            }
            if (phase == "rewrite") CurriculumButton("Review the worked example", !state.busy) { model.answerCurriculum("review") }
        }
        "mastered" -> {
            Text("Concept mastered", style = MaterialTheme.typography.titleLarge)
            Text("Mastery badge earned")
            lesson.optJSONObject("diagnostic_score")?.let { score ->
                Text("Diagnostic score: ${score.getInt("correct")} / ${score.getInt("total")} correct")
            }
            Text("Elapsed time: ${lesson.getInt("elapsed_seconds")} seconds")
            Text("Verified against the lesson's answer and explanation checklist.")
            if (chapter != null) {
                val next = state.curriculumChapters
                    .dropWhile { it.getString("id") != chapter.getString("id") }
                    .drop(1)
                    .firstOrNull {
                        it.getInt("grade") == chapter.getInt("grade") &&
                            it.getString("subject") == chapter.getString("subject") &&
                            !it.getBoolean("locked") && !it.getBoolean("mastered")
                    }
                if (next != null) {
                    CurriculumButton("Continue to ${next.getString("title")}", !state.busy) {
                        model.openCurriculumChapter(next.getString("id"))
                    }
                }
            }
        }
    }
    CurriculumButton("Back to chapters", !state.busy, model::closeCurriculumChapter)
}

@Composable
fun ReadinessBreakdown(scores: org.json.JSONObject) {
    listOf("fractions" to "Fractions", "decimals" to "Decimals", "percentages" to "Percentages",
        "grade6-algebra" to "Algebra", "grade6-geometry" to "Geometry").forEach { (key, label) ->
        scores.optJSONObject(key)?.let { score ->
            Text("$label: ${score.getInt("correct")} / ${score.getInt("total")}")
        }
    }
}

private fun nextCurriculumChapter(
    chapters: List<org.json.JSONObject>,
    studiedSubjects: Set<String> = emptySet(),
): org.json.JSONObject? {
    val available = chapters.filter { !it.getBoolean("locked") && !it.getBoolean("mastered") }
    return available.filter { it.optBoolean("needs_practice") }.maxByOrNull { it.optInt("review_events") }
        ?: available.firstOrNull { it.optBoolean("started") }
        ?: available.firstOrNull { it.getString("subject") in studiedSubjects }
        ?: available.firstOrNull()
}

@Composable
private fun CurriculumButton(text: String, enabled: Boolean, action: () -> Unit) {
    OutlinedButton(onClick = action, enabled = enabled, modifier = Modifier.fillMaxWidth()) { Text(text) }
}
