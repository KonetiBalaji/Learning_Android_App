package com.studycompanion

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.studycompanion.data.objects
import com.studycompanion.data.strings
import org.json.JSONObject

@Composable fun OfflineStudyScreen(state: StudyState, model: StudyViewModel) {
    Text("Offline study", style = MaterialTheme.typography.headlineMedium)
    Text("Easy passage recall on this device. Local progress is not yet synced to your account.")
    val bundle = state.offlineBundle
    if (bundle == null) {
        if (state.offlineDocuments.isEmpty()) Text("No material saved. Open a document online and save its confirmed material first.")
        state.offlineDocuments.forEach { doc ->
            OutlinedButton(onClick = { model.openOffline(doc.getString("id")) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Open saved ${doc.getString("title")}") }
        }
        TextButton(onClick = { model.navigate("home") }, enabled = !state.busy) { Text("Back to library") }
        return
    }
    val doc = bundle.getJSONObject("document")
    val docId = doc.getString("id")
    Text(doc.getString("title"), style = MaterialTheme.typography.titleLarge)
    Text("Available until " + java.text.DateFormat.getDateTimeInstance().format(java.util.Date((bundle.getDouble("expires_at") * 1000).toLong())))
    val sessions = bundle.optJSONArray("local_quizzes")?.objects().orEmpty()
    val quiz = sessions.find { it.getString("id") == state.offlineQuizId }
    var sourceId by rememberSaveable(docId) { mutableStateOf<String?>(null) }
    var remove by rememberSaveable(docId) { mutableStateOf(false) }
    if (sourceId != null) {
        val source = bundle.getJSONArray("passages").objects().find { it.getString("id") == sourceId }
        AlertDialog(onDismissRequest = { sourceId = null }, title = { Text("Saved source passage") }, text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                source?.let {
                    Text(offlineSection(doc, it.getString("section_id")))
                    if (doc.getBoolean("has_real_pages")) Text("Page ${it.getInt("page")}")
                    Text(it.getString("text"))
                }
            }
        }, confirmButton = { TextButton(onClick = { sourceId = null }) { Text("Close saved source") } })
    }
    if (remove) AlertDialog(onDismissRequest = { remove = false }, title = { Text("Remove saved copy?") },
        text = { Text("This removes this device's saved material and its local sessions, including unsynced answers. The online document remains available.") },
        confirmButton = { TextButton(onClick = { remove = false; model.removeOffline(docId) }) { Text("Remove offline copy and local sessions") } },
        dismissButton = { TextButton(onClick = { remove = false }) { Text("Keep saved copy") } })
    if (quiz == null) {
        var selected by rememberSaveable(docId) { mutableStateOf(emptyList<String>()) }
        var count by rememberSaveable(docId) { mutableStateOf(minOf(10, bundle.getJSONArray("passages").length()).toString()) }
        var kind by rememberSaveable(docId) { mutableStateOf("multiple_choice") }
        var first by rememberSaveable(docId) { mutableStateOf("") }
        var last by rememberSaveable(docId) { mutableStateOf("") }
        Text("Select saved chapters (leave all unchecked for the whole document)")
        doc.getJSONArray("sections").objects().forEach { section ->
            Row {
                Checkbox(checked = section.getString("id") in selected, enabled = !state.busy,
                    onCheckedChange = { checked -> selected = if (checked) selected + section.getString("id") else selected - section.getString("id") })
                Text(section.getString("title"), modifier = Modifier.weight(1f))
            }
        }
        if (doc.getBoolean("has_real_pages")) {
            OutlinedTextField(first, { first = it }, label = { Text("Offline first page") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), enabled = !state.busy)
            OutlinedTextField(last, { last = it }, label = { Text("Offline last page") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), enabled = !state.busy)
        }
        Text("Topic search and AI explanations require the online tools. Offline selection uses chapters and pages.")
        OutlinedTextField(count, { count = it }, label = { Text("Offline questions · 1–50") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), enabled = !state.busy)
        listOf("multiple_choice" to "Multiple choice", "true_false" to "True / False", "yes_no" to "Yes / No").forEach { (value, label) ->
            Row { RadioButton(selected = kind == value, onClick = { kind = value }, enabled = !state.busy); Text(label) }
        }
        Button(onClick = { model.startOffline(selected.toSet(), first, last, count.toInt(), kind) }, enabled = !state.busy && count.toIntOrNull()?.let { it in 1..50 } == true, modifier = Modifier.fillMaxWidth()) { Text("Generate offline practice") }
        sessions.reversed().forEach { session ->
            val done = session.getInt("index") >= session.getJSONArray("questions").length()
            OutlinedButton(onClick = { model.resumeOffline(session.getString("id")) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                Text(if (done) "Review saved offline result · ${session.getJSONArray("questions").length()} questions" else "Resume offline practice · question ${session.getInt("index") + 1}")
            }
        }
        TextButton(onClick = { remove = true }, enabled = !state.busy) { Text("Remove this offline copy") }
        TextButton(onClick = model::showOffline, enabled = !state.busy) { Text("Back to saved material") }
        return
    }
    val questions = quiz.getJSONArray("questions").objects()
    val answers = quiz.getJSONArray("answers")
    val index = quiz.getInt("index")
    if (index >= questions.size) {
        val correct = questions.countIndexed { i, question -> answers.getInt(i) == question.getInt("answer") }
        Text("Offline result: $correct / ${questions.size}", style = MaterialTheme.typography.headlineSmall)
        Text("Saved on this device · not yet synced")
        questions.forEachIndexed { i, question ->
            if (answers.getInt(i) != question.getInt("answer")) {
                Text(question.getString("prompt"), style = MaterialTheme.typography.titleMedium)
                Text("Correct: " + question.getJSONArray("choices").getString(question.getInt("answer")))
                Text(question.getString("explanation"))
                TextButton(onClick = { sourceId = question.getString("source_id") }) { Text("Read saved source") }
            }
        }
        if (correct < questions.size) Button(onClick = model::retryOffline, enabled = !state.busy) { Text("Retry offline mistakes") }
    } else {
        val question = questions[index]
        var selected by rememberSaveable(quiz.getString("id"), index) { mutableStateOf<Int?>(null) }
        val answered = answers.length() > index
        Text("Offline question ${index + 1} of ${questions.size}", style = MaterialTheme.typography.titleLarge)
        Text(question.getString("prompt"))
        question.getJSONArray("choices").strings().forEachIndexed { choice, label ->
            OutlinedButton(onClick = { selected = choice }, enabled = !state.busy && !answered, modifier = Modifier.fillMaxWidth()) {
                RadioButton(selected = (if (answered) answers.getInt(index) else selected) == choice, onClick = null)
                Text(label)
            }
        }
        if (!answered) Button(onClick = { selected?.let(model::answerOffline) }, enabled = !state.busy && selected != null) { Text("Check offline answer") }
        else {
            Text(if (answers.getInt(index) == question.getInt("answer")) "Correct" else "Let's learn from this")
            Text("Correct: " + question.getJSONArray("choices").getString(question.getInt("answer")))
            Text(question.getString("explanation"))
            TextButton(onClick = { sourceId = question.getString("source_id") }) { Text("Read saved source") }
            Button(onClick = model::nextOffline, enabled = !state.busy) { Text(if (index + 1 == questions.size) "See offline results" else "Next offline question") }
        }
    }
    TextButton(onClick = { model.resumeOffline(null) }, enabled = !state.busy) { Text("Back to offline sessions") }
}

private fun offlineSection(doc: JSONObject, id: String) = doc.getJSONArray("sections").objects().find { it.getString("id") == id }?.getString("title") ?: "Source section"
private inline fun <T> List<T>.countIndexed(predicate: (Int, T) -> Boolean) = mapIndexed(predicate).count { it }
