package com.studycompanion

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.core.view.WindowCompat
import com.studycompanion.data.objects
import com.studycompanion.data.strings
import com.studycompanion.domain.QuizRules
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = true
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(
                primary = Color(0xFF246B5C), onPrimary = Color.White,
                primaryContainer = Color(0xFFD7EEE3), onPrimaryContainer = Color(0xFF163D33), secondary = Color(0xFF536A82),
                surfaceVariant = Color(0xFFE8EEE9), onSurfaceVariant = Color(0xFF47534D),
                background = Color(0xFFF6F7F2), surface = Color(0xFFFFFEFA)
            )) {
                StudyApp()
            }
        }
    }
}

@Composable
fun StudyApp(model: StudyViewModel = viewModel()) {
    val state by model.state.collectAsStateWithLifecycle()
    val screenScroll = key(state.screen, state.quiz?.optString("id"), state.quiz?.optInt("index")) { rememberScrollState() }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> uri?.let(model::upload) }
    var confirmation by remember { mutableStateOf<String?>(null) }
    BackHandler(state.signedIn && state.screen != "home") {
        if (!state.busy) model.navigate(if (state.screen == "mistakes") "results" else "home")
    }
    Scaffold(
        topBar = {
            Surface(shadowElevation = 1.dp) {
                Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 20.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("SARAS", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                        Text("A little practice. Real progress.", style = MaterialTheme.typography.bodySmall)
                    }
                    if (state.signedIn && state.screen != "home") TextButton(enabled = !state.busy, onClick = { model.navigate("home") }) { Text("Home") }
                }
            }
        },
        bottomBar = {
            if (state.signedIn) Surface(tonalElevation = 3.dp) {
                Row(Modifier.fillMaxWidth().navigationBarsPadding(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    listOf("home" to "Library", "progress" to "Progress", "settings" to "Settings").forEach { (screen, label) ->
                        TextButton(enabled = !state.busy, onClick = { model.navigate(screen) }) { Text(label, fontWeight = if (state.screen == screen) FontWeight.Bold else FontWeight.Normal) }
                    }
                    TextButton(enabled = !state.busy, onClick = { model.showFlashcards() }) { Text("Review") }
                }
            }
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(screenScroll).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)) {
            if (state.busy) {
                LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(if (state.uploadProgress != null) {
                    if (state.uploadProgress == 100) "Analyzing document…" else "Uploading ${state.uploadProgress}%…"
                } else "Working…", style = MaterialTheme.typography.bodySmall)
            }
            state.error?.let { error ->
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Column(Modifier.padding(16.dp)) {
                        Text(error, color = MaterialTheme.colorScheme.onErrorContainer)
                        Row {
                            TextButton(enabled = !state.busy, onClick = model::retry) { Text("Retry") }
                            TextButton(onClick = model::dismissError) { Text("Dismiss") }
                        }
                    }
                }
            }
            if (!state.signedIn) Login(model, state.busy)
            else when (state.screen) {
                "home" -> {
                    Title("Your learning library", "Turn your own material into a focused practice session.")
                    PracticeNotice(state.aiMode)
                    Button(onClick = { picker.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain")) },
                        enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("+ Upload study material") }
                    Text("PDF, DOCX or UTF-8 TXT · up to 50 MB", style = MaterialTheme.typography.bodySmall)
                    val active = state.progress?.optJSONArray("in_progress")?.objects().orEmpty()
                    if (active.isNotEmpty()) {
                        Text("Continue studying", style = MaterialTheme.typography.titleMedium)
                        active.forEach { quiz ->
                            OutlinedButton(onClick = { model.resume(quiz.getString("id")) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                                Text("Resume ${documentTitle(state, quiz.getString("document_id"))} · ${quiz.getInt("index") + 1}/${quiz.getInt("count")}")
                            }
                        }
                    }
                    if (state.documents.isEmpty() && !state.busy) Info("Your library is ready", "Upload your first document. Chapters will appear here after analysis.")
                    state.documents.forEach { doc ->
                        Card(Modifier.fillMaxWidth().clickable(enabled = !state.busy) { model.openDocument(doc) }) {
                            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(doc.getString("title"), style = MaterialTheme.typography.titleLarge)
                                Text("${doc.getJSONArray("sections").length()} sections · ${if (doc.getBoolean("has_real_pages")) "${doc.getInt("page_count")} pages" else "text document"}", style = MaterialTheme.typography.bodySmall)
                                Text("Choose what to study →", color = MaterialTheme.colorScheme.primary)
                            }
                        }
                    }
                    TextButton(onClick = model::refresh, enabled = !state.busy) { Text("Refresh library") }
                }
                "configure" -> state.document?.let { doc -> Configure(doc, state.busy, state.aiMode, model) { confirmation = "document" } }
                "quiz" -> state.quiz?.let { quiz -> Question(quiz, state.busy, model) }
                "results" -> state.results?.let { result -> Results(result, state, model) }
                "mistakes" -> state.results?.let { result ->
                    Title("Learn from the tricky ones", "Read the original passage, then try again.")
                    result.getJSONArray("mistakes").objects().forEach { mistake ->
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                val question = mistake.getJSONObject("question")
                                Text(question.getString("prompt"), style = MaterialTheme.typography.titleMedium)
                                Feedback(question, mistake.getJSONObject("feedback"))
                                TextButton(onClick = { model.showSource(question.getString("source_id")) }, enabled = !state.busy) { Text("Read source passage") }
                            }
                        }
                    }
                    Button(onClick = model::retryMistakes, enabled = !state.busy) { Text("Retry incorrect questions") }
                    TextButton(onClick = { model.navigate("results") }) { Text("Back to results") }
                }
                "progress" -> Progress(state, model)
                "flashcards" -> Flashcards(state, model)
                "settings" -> {
                    Title("Your study space", "Privacy and account settings")
                    PracticeNotice(state.aiMode)
                    Info("Server", model.session.server)
                    Info("Your data", "Document text and quizzes are encrypted in the local backend database. Uploaded originals are discarded after extraction. Documents and related progress expire after 30 days. Delete a document from its study screen, or delete your account below.")
                    Info("Connection", "Debug builds allow HTTP only to the emulator host and localhost. Use HTTPS for a deployed server. Your session is protected by Android Keystore.")
                    OutlinedButton(onClick = model::signOut, enabled = !state.busy) { Text("Sign out") }
                    TextButton(onClick = { confirmation = "account" }, enabled = !state.busy) { Text("Delete account and all data", color = MaterialTheme.colorScheme.error) }
                }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
    state.source?.let { source ->
        AlertDialog(onDismissRequest = model::hideSource, title = { Text("Source passage") },
            text = { Column(Modifier.verticalScroll(rememberScrollState())) {
                Text(sectionTitle(state.document, source.getString("section_id")), style = MaterialTheme.typography.labelLarge)
                if (state.document?.optBoolean("has_real_pages") == true) Text("Page ${source.getInt("page")}")
                Spacer(Modifier.height(12.dp)); Text(source.getString("text"))
            } }, confirmButton = { TextButton(onClick = model::hideSource) { Text("Close") } })
    }
    confirmation?.let { kind ->
        AlertDialog(onDismissRequest = { confirmation = null }, title = { Text(if (kind == "account") "Delete your account?" else "Delete this document?") },
            text = { Text("This permanently removes the selected data and its quiz history from the server.") },
            confirmButton = { TextButton(onClick = {
                confirmation = null
                if (kind == "account") model.deleteAccount() else state.document?.getString("id")?.let(model::deleteDocument)
            }) { Text("Delete", color = MaterialTheme.colorScheme.error) } },
            dismissButton = { TextButton(onClick = { confirmation = null }) { Text("Keep studying") } })
    }
}

@Composable private fun Title(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        Text(subtitle, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable private fun Info(title: String, body: String) {
    Surface(color = MaterialTheme.colorScheme.surfaceVariant, shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, fontWeight = FontWeight.SemiBold); Text(body, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable private fun PracticeNotice(aiMode: Boolean = false) {
    if (aiMode) Info("Source-grounded AI practice", "Questions use your selected material. Read the source passage with each explanation. Selected passages are sent to the server’s AI provider to create and review questions.")
    else Info("Local practice mode", "Practice recall using exact passages from your material. AI concept questions and higher difficulty will be available after the provider is connected.")
}

@Composable private fun Login(model: StudyViewModel, busy: Boolean) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var server by rememberSaveable { mutableStateOf(model.session.server) }
    var register by rememberSaveable { mutableStateOf(true) }
    Title("Make room for understanding.", "Upload your notes. Practice one question at a time. Learn from every answer.")
    PracticeNotice()
    OutlinedTextField(username, { username = it }, label = { Text("Username") }, singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    OutlinedTextField(password, { password = it }, label = { Text("Password · 10+ characters") }, visualTransformation = PasswordVisualTransformation(), singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    OutlinedTextField(server, { server = it }, label = { Text("Study server URL") }, supportingText = { Text("Android emulator: http://10.0.2.2:8000") }, singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    Button(onClick = { model.authenticate(username, password, register, server); password = "" }, enabled = !busy && username.length >= 3 && password.length >= 10, modifier = Modifier.fillMaxWidth()) {
        Text(if (register) "Create your study account" else "Sign in")
    }
    TextButton(onClick = { register = !register }, enabled = !busy) { Text(if (register) "Already have an account? Sign in" else "New here? Create an account") }
}

@Composable private fun Configure(doc: JSONObject, busy: Boolean, aiMode: Boolean, model: StudyViewModel, delete: () -> Unit) {
    val id = doc.getString("id")
    var selected by rememberSaveable(id) { mutableStateOf(emptyList<String>()) }
    var count by rememberSaveable(id) { mutableStateOf("10") }
    var kind by rememberSaveable(id) { mutableStateOf("multiple_choice") }
    var first by rememberSaveable(id) { mutableStateOf("") }
    var last by rememberSaveable(id) { mutableStateOf("") }
    var topic by rememberSaveable(id) { mutableStateOf("") }
    var difficulty by rememberSaveable(id) { mutableStateOf("easy") }
    Title(doc.getString("title"), "Choose a focus for today")
    if (doc.getString("structure_confidence") == "uncertain") Info("Review the detected structure", "We could not confidently split chapters. Study the whole document, search a topic, or choose a PDF page range.")
    Text("Chapters & sections", style = MaterialTheme.typography.titleMedium)
    Text("No selection means the entire document. Selected sections, pages and topic filters are combined.", style = MaterialTheme.typography.bodySmall)
    doc.getJSONArray("sections").objects().forEach { section ->
        val sectionId = section.getString("id")
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth().padding(start = if (section.isNull("parent_id")) 0.dp else 20.dp)) {
            Checkbox(checked = sectionId in selected, onCheckedChange = { checked -> selected = if (checked) selected + sectionId else selected - sectionId }, enabled = !busy)
            Text(section.getString("title"), modifier = Modifier.weight(1f))
        }
    }
    if (doc.getBoolean("has_real_pages")) Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(first, { first = it }, label = { Text("First page") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f), enabled = !busy)
        OutlinedTextField(last, { last = it }, label = { Text("Last page") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.weight(1f), enabled = !busy)
    }
    OutlinedTextField(topic, { topic = it }, label = { Text("Topic keywords (optional)") }, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    OutlinedTextField(count, { count = it }, label = { Text("Questions · 1–50") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), isError = QuizRules.questionCount(count) == null, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    Text("Question format", style = MaterialTheme.typography.titleMedium)
    listOf("multiple_choice" to "Multiple choice", "true_false" to "True / False", "yes_no" to "Yes / No").forEach { (value, label) ->
        Row(verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = kind == value, onClick = { kind = value }, enabled = !busy); Text(label)
        }
    }
    if (aiMode) {
        PracticeNotice(true)
        Text("Difficulty", style = MaterialTheme.typography.titleMedium)
        listOf("easy", "medium", "hard", "mixed").forEach { value ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = difficulty == value, onClick = { difficulty = value }, enabled = !busy)
                Text(value.replaceFirstChar { it.uppercase() })
            }
        }
    } else Info("Difficulty: Easy", "Local practice checks exact recall. Medium, Hard and semantic Mixed difficulty require AI generation, which is deferred.")
    Button(enabled = !busy && QuizRules.questionCount(count) != null, onClick = {
        model.startQuiz(selected.toSet(), count.toInt(), kind, if (aiMode) difficulty else "easy", first, last, topic)
    }, modifier = Modifier.fillMaxWidth()) { Text("Start practice") }
    TextButton(onClick = delete, enabled = !busy) { Text("Delete document", color = MaterialTheme.colorScheme.error) }
}

@Composable private fun Question(quiz: JSONObject, busy: Boolean, model: StudyViewModel) {
    if (quiz.getBoolean("complete")) return
    val question = quiz.getJSONObject("question")
    val feedback = quiz.optJSONObject("feedback")
    var selected by rememberSaveable(quiz.getString("id"), question.getString("id")) { mutableStateOf<Int?>(null) }
    val index = quiz.getInt("index")
    val count = quiz.getInt("count")
    Title("Question ${index + 1} of $count", "Take your time. Understanding comes with practice.")
    LinearProgressIndicator(progress = { (index.toFloat() / count) }, modifier = Modifier.fillMaxWidth())
    Text(question.getString("prompt"), style = MaterialTheme.typography.titleLarge)
    question.getJSONArray("choices").strings().forEachIndexed { choice, label ->
        val checked = (feedback?.optInt("selected") ?: selected) == choice
        OutlinedCard(onClick = { selected = choice }, enabled = !busy && feedback == null, modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.outlinedCardColors(containerColor = if (checked) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface)) {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = checked, onClick = null)
                Spacer(Modifier.width(12.dp)); Text(label)
            }
        }
    }
    if (feedback == null) Button(onClick = { selected?.let(model::answer) }, enabled = QuizRules.canSubmit(selected, false, busy), modifier = Modifier.fillMaxWidth()) { Text("Check answer") }
    else {
        Feedback(question, feedback)
        TextButton(onClick = { model.showSource(question.getString("source_id")) }, enabled = !busy) { Text("Read source passage") }
        Button(onClick = model::next, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text(if (index + 1 == count) "See my results" else "Next question") }
    }
}

@Composable private fun Feedback(question: JSONObject, feedback: JSONObject) {
    val choices = question.getJSONArray("choices")
    Info(if (feedback.getBoolean("correct")) "Correct ✓" else "Not quite — let’s revisit it",
        "Your answer: ${choices.getString(feedback.getInt("selected"))}\nCorrect answer: ${choices.getString(feedback.getInt("answer"))}\n\n${feedback.getString("explanation")}")
}

@Composable private fun Results(result: JSONObject, state: StudyState, model: StudyViewModel) {
    Title("A session well spent.", "You completed ${result.getInt("total")} questions.")
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(24.dp)) {
            Text("${result.getInt("accuracy")}%", style = MaterialTheme.typography.displayLarge)
            Text("${result.getInt("correct")} correct · ${result.getInt("incorrect")} to revisit", style = MaterialTheme.typography.titleMedium)
        }
    }
    result.getJSONArray("concepts").objects().forEach { concept ->
        Info(sectionTitle(state.document, concept.getString("id")), "${concept.getInt("correct")} / ${concept.getInt("total")} correct · ${if (concept.getInt("correct") == concept.getInt("total")) "Strong this session" else "Keep practicing"}")
    }
    if (result.getInt("incorrect") > 0) {
        Button(onClick = { model.navigate("mistakes") }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Review mistakes") }
        OutlinedButton(onClick = model::retryMistakes, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Retry incorrect questions") }
    }
    OutlinedButton(onClick = { model.navigate("configure") }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Choose material & practice again") }
    Button(onClick = { model.makeFlashcards() }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Create flashcards for spaced review") }
    if (result.getInt("incorrect") > 0) TextButton(onClick = { model.makeFlashcards(true) }, enabled = !state.busy) { Text("Make cards from mistakes only") }
}

@Composable private fun Flashcards(state: StudyState, model: StudyViewModel) {
    Title("Make it stick", if (state.dueOnly) "Cards ready for spaced review" else "All your source-backed flashcards")
    if (state.flashcards.isEmpty()) {
        Info("Nothing due right now", "Create flashcards from a completed quiz. Your ratings determine when each card returns.")
        if (state.dueOnly) OutlinedButton(onClick = { model.showFlashcards(false) }, enabled = !state.busy) { Text("Browse all cards") }
        return
    }
    var position by rememberSaveable { mutableIntStateOf(0) }
    val card = state.flashcards[position.coerceIn(0, state.flashcards.lastIndex)]
    val review = card.getJSONObject("review")
    var revealed by rememberSaveable(card.getString("id"), review.getInt("version")) { mutableStateOf(false) }
    Text("${state.flashcards.size} cards ${if (state.dueOnly) "ready" else "saved"}", style = MaterialTheme.typography.labelLarge)
    Text(card.getString("front"), style = MaterialTheme.typography.titleLarge)
    if (!revealed) Button(onClick = { revealed = true }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Reveal answer") }
    else {
        Info(card.getString("back"), card.getString("explanation"))
        TextButton(onClick = { model.showCardSource(card) }, enabled = !state.busy) { Text("Read source passage") }
        Text("How well did you recall it?", style = MaterialTheme.typography.titleMedium)
        listOf(0 to "Again — I forgot", 3 to "Hard — serious effort", 4 to "Good — after a pause", 5 to "Easy — immediate recall").forEach { (quality, label) ->
            OutlinedButton(onClick = { model.rateFlashcard(card, quality) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text(label) }
        }
        Text("Hard and Again stay in today’s learning queue. Good and Easy schedule the next review.", style = MaterialTheme.typography.bodySmall)
    }
    if (state.flashcards.size > 1) TextButton(onClick = { position = (position + 1) % state.flashcards.size }, enabled = !state.busy) { Text("Skip to another card") }
    TextButton(onClick = { model.showFlashcards(!state.dueOnly) }, enabled = !state.busy) { Text(if (state.dueOnly) "Browse all cards" else "Show due cards") }
    if (state.results != null) TextButton(onClick = { model.navigate("results") }, enabled = !state.busy) { Text("Back to results") }
}

@Composable private fun Progress(state: StudyState, model: StudyViewModel) {
    Title("See how far you’ve come", "Every session is another step forward.")
    val progress = state.progress
    if (progress == null) Text("Refresh to load your learning progress.")
    else {
        Info("Your practice so far", "${progress.getInt("quizzes_completed")} sessions · ${progress.getInt("questions_answered")} answers\nAccuracy: ${if (progress.isNull("accuracy")) "Not started" else "${progress.getInt("accuracy")}%"}")
        progress.optJSONArray("documents")?.objects()?.forEach { document ->
            Text(document.getString("title"), style = MaterialTheme.typography.titleMedium)
            document.getJSONArray("sections").objects().forEach { section ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(section.getString("title"), modifier = Modifier.weight(1f))
                    Text(if (section.isNull("accuracy")) "Not started" else "${section.getInt("accuracy")}%", fontWeight = FontWeight.SemiBold)
                }
            }
        }
        val history = progress.getJSONArray("history").objects()
        if (history.isEmpty()) Text("Complete a quiz to start tracking progress.")
        history.forEach { item ->
            OutlinedCard(onClick = { model.showResults(item.getString("id")) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(documentTitle(state, item.getString("document_id")), style = MaterialTheme.typography.titleMedium)
                    Text("${item.getInt("correct")} / ${item.getInt("total")} · ${item.getInt("accuracy")}%")
                }
            }
        }
    }
    TextButton(onClick = model::refresh, enabled = !state.busy) { Text("Refresh progress") }
}

private fun sectionTitle(doc: JSONObject?, id: String): String = doc?.optJSONArray("sections")?.objects()?.find { it.getString("id") == id }?.getString("title") ?: id
private fun documentTitle(state: StudyState, id: String): String = state.documents.find { it.getString("id") == id }?.getString("title") ?: "Study session"
