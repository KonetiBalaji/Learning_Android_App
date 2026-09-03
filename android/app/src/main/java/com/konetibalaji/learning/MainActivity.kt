package com.konetibalaji.learning

import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.School
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { LearnSmartApp() } }
}

private val Indigo = Color(0xFF4F46E5)
private val Blue = Color(0xFF2563EB)
private val Success = Color(0xFF10B981)
private val Warning = Color(0xFFF59E0B)
private val Muted = Color(0xFF64748B)
private val Canvas = Color(0xFFF8FAFC)

@Composable
private fun LearnSmartApp(viewModel: LearningViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val colors = if (state.darkMode) darkColorScheme(primary = Color(0xFFA5B4FC), secondary = Color(0xFF93C5FD), tertiary = Color(0xFF6EE7B7)) else lightColorScheme(primary = Indigo, secondary = Blue, tertiary = Success, background = Canvas, surface = Color.White)
    MaterialTheme(colorScheme = colors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
                Box(Modifier.fillMaxSize().padding(padding)) {
                    when (state.screen) {
                        Screen.SignIn -> SignInScreen(state.loading, viewModel::authenticate)
                        Screen.Grade -> GradeScreen(viewModel::selectGrade)
                        Screen.Subjects -> SubjectsScreen(state, viewModel::selectSubject, viewModel::openParentDashboard, viewModel::startDocumentStudy, viewModel::openSettings, viewModel::resumeLearning, viewModel::resumeDocumentQuiz)
                        Screen.MasteryChapters -> ChapterScreen(state, viewModel::selectMasteryChapter, viewModel::backToSubjects)
                        Screen.Diagnostic -> DiagnosticScreen(state, viewModel::selectDiagnosticAnswer, viewModel::submitDiagnostic)
                        Screen.Tutor -> TutorScreen(state, viewModel::startPractice)
                        Screen.Practice -> PracticeScreen(state, viewModel::showHint, viewModel::checkPractice, viewModel::moveToRewrite)
                        Screen.Rewrite -> RewriteScreen(state, viewModel::updateRewrite, viewModel::submitRewrite)
                        Screen.Mastery -> MasteryScreen(state, viewModel::continueFromMastery)
                        Screen.ParentDashboard -> ParentDashboard(state, viewModel::backToSubjects)
                        Screen.Home -> StudyMaterialScreen(state.loading, viewModel::upload, viewModel::backToSubjects)
                        Screen.Chapters -> DocumentChaptersScreen(state, viewModel::selectChapter, viewModel::createQuiz)
                        Screen.Question -> DocumentQuestionScreen(state, viewModel::submitAnswer)
                        Screen.Feedback -> DocumentFeedbackScreen(state.feedback, viewModel::continueAfterFeedback)
                        Screen.Results -> DocumentResultsScreen(state.results, viewModel::startAnotherDocument, viewModel::backToSubjects)
                        Screen.Settings -> SettingsScreen(state, viewModel::backToSubjects, viewModel::setDarkMode, viewModel::changeGrade, viewModel::signOut, viewModel::deleteAccount)
                    }
                    if (state.loading) LoadingOverlay()
                }
            }
        }
    }
    state.error?.let { ErrorDialog(it, viewModel::clearError) }
}

@Composable
private fun Page(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) = Column(
    modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 30.dp),
    verticalArrangement = Arrangement.spacedBy(18.dp), content = content,
)

@Composable
private fun Header(eyebrow: String, title: String, body: String) = Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
    Text(eyebrow.uppercase(), color = Indigo, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
    Text(title, color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
    Text(body, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyLarge)
}

@Composable
private fun PrimaryButton(label: String, enabled: Boolean = true, onClick: () -> Unit) = Button(
    onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().height(54.dp), shape = RoundedCornerShape(16.dp),
    colors = ButtonDefaults.buttonColors(containerColor = Indigo),
) { Text(label, fontWeight = FontWeight.Bold) }

@Composable
private fun SignInScreen(loading: Boolean, onAuthenticate: (String, String, Boolean) -> Unit) {
    var email by remember { mutableStateOf("") }; var password by remember { mutableStateOf("") }; var createAccount by remember { mutableStateOf(false) }
    Page(modifier = Modifier.padding(top = 22.dp)) {
        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFEDE9FE)), shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("✦", style = MaterialTheme.typography.displayMedium, color = Indigo)
                Text("LEARN SMART AI", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold, color = Indigo)
                Text("Your personal learning coach", color = Muted)
            }
        }
        Header(if (createAccount) "New learner" else "Welcome back", if (createAccount) "Create your account." else "Learn at your pace.", "Discover what you know, practise what you need, and master every concept.")
        OutlinedTextField(email, { email = it }, Modifier.fillMaxWidth(), label = { Text("Email") }, singleLine = true, shape = RoundedCornerShape(14.dp))
        OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), label = { Text("Password") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), supportingText = { Text("At least 12 characters") }, shape = RoundedCornerShape(14.dp))
        PrimaryButton(if (createAccount) "Create account" else "Sign in", !loading && email.isNotBlank() && password.length >= 12) { onAuthenticate(email.trim(), password, createAccount) }
        TextButton(onClick = { createAccount = !createAccount }, modifier = Modifier.fillMaxWidth()) { Text(if (createAccount) "Already have an account? Sign in" else "New student? Create a private account") }
    }
}

@Composable
private fun GradeScreen(onSelect: (Int) -> Unit) = Page {
    Text("👋 Hello, learner", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
    Header("Your learning path", "Select your grade", "We use your grade to explain concepts at the right level.")
    LazyVerticalGrid(columns = GridCells.Fixed(3), modifier = Modifier.fillMaxWidth().height(330.dp), contentPadding = PaddingValues(2.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        items((1..12).toList()) { grade ->
            Card(modifier = Modifier.fillMaxWidth().height(84.dp).clickable { onSelect(grade) }, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("Grade\n$grade", textAlign = TextAlign.Center, fontWeight = FontWeight.Bold, color = Indigo) }
            }
        }
    }
    TipCard("You can change this later", "Your tutor adapts each explanation as you grow.")
}

@Composable
private fun SubjectsScreen(state: AppUiState, onSelect: (LearningSubject) -> Unit, onParent: () -> Unit, onDocuments: () -> Unit, onSettings: () -> Unit, onResume: () -> Unit, onResumeDocument: () -> Unit) = Page {
    Header("Grade ${state.grade ?: 6}", "What would you like to learn?", "Pick a subject to continue your personalised path.")
    if (state.canResumeMastery) PrimaryButton("Resume saved learning", !state.loading, onResume)
    if (state.canResumeDocumentQuiz) PrimaryButton("Resume document quiz", !state.loading, onResumeDocument)
    LazyVerticalGrid(columns = GridCells.Fixed(2), modifier = Modifier.fillMaxWidth().height(390.dp), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        items(learningSubjects) { subject ->
            val progress = state.progressSnapshot?.subjects?.get(subject.id)
            Card(modifier = Modifier.fillMaxWidth().height(178.dp).clickable { onSelect(subject) }, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(22.dp), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(subject.icon, style = MaterialTheme.typography.headlineLarge, color = Indigo)
                    Text(subject.title, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                    LinearProgressIndicator(progress = { (progress ?: 0) / 100f }, modifier = Modifier.fillMaxWidth(), color = Success, trackColor = Color(0xFFE2E8F0))
                    Text(if (progress == null) "No assessment yet" else "$progress% assessed progress", color = Muted, style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
    OutlinedButton(onClick = onParent, modifier = Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(16.dp)) { Text("View parent & teacher progress") }
    TextButton(onClick = onDocuments, modifier = Modifier.fillMaxWidth()) { Text("Study from my own document") }
    TextButton(onClick = onSettings, modifier = Modifier.fillMaxWidth()) { Text("Settings and account") }
}

@Composable
private fun ChapterScreen(state: AppUiState, onSelect: (MasteryChapter) -> Unit, onBack: () -> Unit) = Page {
    TextButton(onClick = onBack) { Text("‹ All subjects") }
    Header(state.subject?.title ?: "Mathematics", "Choose a chapter", "Master a concept to unlock what comes next.")
    (chaptersBySubject[state.subject?.id] ?: emptyList()).forEach { chapter ->
        val effectivelyLocked = chapter.locked && "${state.subject?.id}:${chapter.id}" !in state.unlockedChapterIds
        val progress = state.progressSnapshot?.chapterScores?.get("${state.subject?.id}:${chapter.id}") ?: 0
        Card(modifier = Modifier.fillMaxWidth().clickable(enabled = !effectivelyLocked) { onSelect(chapter) }, colors = CardDefaults.cardColors(containerColor = if (effectivelyLocked) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp)) {
            Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Text(if (effectivelyLocked) "🔒" else if (progress >= 80) "✓" else "•", color = if (effectivelyLocked) Muted else Success, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text(chapter.title, fontWeight = FontWeight.Bold, color = if (effectivelyLocked) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface)
                    if (effectivelyLocked) Text("Master the previous chapter to unlock", color = Muted, style = MaterialTheme.typography.bodySmall)
                    else if (progress == 0) Text("New chapter", color = Indigo, style = MaterialTheme.typography.bodySmall) else LinearProgressIndicator(progress = { progress / 100f }, color = Success, trackColor = Color(0xFFE2E8F0), modifier = Modifier.fillMaxWidth())
                }
                if (!effectivelyLocked && progress > 0) Text("$progress%", color = Muted, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun DiagnosticScreen(state: AppUiState, onSelect: (String) -> Unit, onSubmit: () -> Unit) {
    val question = state.adaptiveQuestion ?: fractionQuestions[state.diagnosticIndex]
    Page {
        RewriteAssessmentFeedback(state)
        Text("${state.subject?.title ?: "SUBJECT"}  ›  ${state.masteryChapter?.title ?: "CHAPTER"}".uppercase(), style = MaterialTheme.typography.labelLarge, color = Indigo, fontWeight = FontWeight.Bold)
        LinearProgressIndicator(progress = { state.adaptiveOrdinal / state.adaptiveTotal.toFloat() }, modifier = Modifier.fillMaxWidth(), color = Indigo, trackColor = Color(0xFFE2E8F0))
        Header("Diagnostic quiz", "Question ${state.adaptiveOrdinal} of ${state.adaptiveTotal}", "Choose the answer that makes sense to you.")
        Text(question.prompt, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
        question.options.forEach { option -> AnswerChoice(option, state.selectedDiagnosticAnswer == option) { onSelect(option) }
        }
        PrimaryButton("Submit answer", state.selectedDiagnosticAnswer != null, onSubmit)
    }
}

@Composable
private fun AnswerChoice(option: String, selected: Boolean, onClick: () -> Unit) = Card(
    modifier = Modifier.fillMaxWidth().selectable(selected = selected, onClick = onClick, role = Role.RadioButton), shape = RoundedCornerShape(16.dp),
    colors = CardDefaults.cardColors(containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface), border = if (selected) androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary) else null,
) { Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) { RadioButton(selected, null); Spacer(Modifier.width(12.dp)); Text(option, fontWeight = FontWeight.Medium, color = MaterialTheme.colorScheme.onSurface) } }

@Composable
private fun TutorScreen(state: AppUiState, onUnderstand: () -> Unit) {
    val lesson = state.tutorLesson
    Page {
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF7ED)), shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("✦ AI Teacher", color = Warning, fontWeight = FontWeight.Bold)
            Text("Not quite — let’s build it together.", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Your answer: ${state.selectedDiagnosticAnswer ?: "Needs another look"}", color = Muted)
        }
    }
    Header("A quick explanation", lesson?.title ?: "Add the numerators", lesson?.explanation ?: "When fractions have the same denominator, the pieces are the same size. Keep the denominator and add only the top numbers.")
    RewriteAssessmentFeedback(state)
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Worked example", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = Indigo)
            Text(lesson?.workedExample ?: "3/4 + 1/4 = (3 + 1) / 4 = 4/4 = 1", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)
            HorizontalDivider(Modifier.padding(vertical = 4.dp))
            Text(lesson?.hint ?: "Try this pattern: 2/5 + 3/5 = 5/5 = 1", color = Muted)
        }
    }
    TipCard("Your tutor is paying attention", if (state.coachingRound > 0) "Let’s try a different explanation and practise it once more." else "A short practice question will check that the idea clicked.")
    ReadAloudControls(listOfNotNull(lesson?.title, lesson?.explanation, lesson?.workedExample).joinToString(". "))
    if (state.subject?.id == "math" && state.masteryChapter?.id == "fractions") FractionExplorer()
    PrimaryButton("I understand — practise now", onClick = onUnderstand)
    }
}

@Composable
private fun PracticeScreen(state: AppUiState, onHint: () -> Unit, onCheck: (String) -> Unit, onContinue: () -> Unit) {
    var answer by remember { mutableStateOf("") }
    Page {
        Header("Practice with AI", "Let’s try together.", "Apply the idea from the tutor's explanation.")
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) { Text(state.tutorLesson?.practicePrompt ?: "What is 2/8 + 4/8?", modifier = Modifier.padding(22.dp), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface) }
        OutlinedTextField(answer, { answer = it }, Modifier.fillMaxWidth(), label = { Text("Your answer") }, placeholder = { Text("Example: 6/8") }, singleLine = true, shape = RoundedCornerShape(14.dp))
        VoiceInputButton("Speak my answer") { answer = it }
        if (state.showHint) TipCard("Hint", state.tutorLesson?.hint ?: "Review the tutor explanation, then try again.")
        when (state.practiceResult) {
            true -> Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFECFDF5)), shape = RoundedCornerShape(16.dp)) { Text("Correct! You are ready to explain the idea.", Modifier.padding(16.dp), color = Success, fontWeight = FontWeight.Bold) }
            false -> Text("Almost. Use the hint, then try again.", color = Warning, fontWeight = FontWeight.Medium)
            null -> Unit
        }
        if (state.practiceResult == true) PrimaryButton("Explain it in your own words", onClick = onContinue)
        else { OutlinedButton(onClick = onHint, modifier = Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(16.dp)) { Text("Show hint") }; PrimaryButton("Check answer", answer.isNotBlank()) { onCheck(answer) } }
    }
}

@Composable
private fun RewriteScreen(state: AppUiState, onChange: (String) -> Unit, onSubmit: () -> Unit) = Page {
    Header("Show your thinking", "Explain it in your own words", "Explain ${state.tutorLesson?.title ?: "the concept"} and connect it to the practice example.")
    OutlinedTextField(state.rewrite, onChange, modifier = Modifier.fillMaxWidth().height(190.dp), label = { Text("My explanation") }, placeholder = { Text("I know this equals 1 because…") }, shape = RoundedCornerShape(16.dp))
    VoiceInputButton("Speak my explanation") { spoken -> onChange(listOf(state.rewrite, spoken).filter(String::isNotBlank).joinToString(" ")) }
    TipCard("AI evaluates understanding", "You will receive another friendly coaching step if your explanation needs more detail.")
    PrimaryButton("Submit my explanation", state.rewrite.trim().isNotEmpty(), onSubmit)
}

@Composable
private fun VoiceInputButton(label: String, onResult: (String) -> Unit) {
    var message by remember { mutableStateOf<String?>(null) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val spoken = acceptedSpeech(result.resultCode == android.app.Activity.RESULT_OK, result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS))
        if (spoken != null) { onResult(spoken); message = "Review the recognized text before submitting." }
        else message = if (result.resultCode == android.app.Activity.RESULT_CANCELED) "Voice input cancelled. Your typed answer is unchanged." else "No speech was recognized. Try again or type your answer."
    }
    OutlinedButton(onClick = {
        message = null
        try { launcher.launch(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PROMPT, label)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US")
        }) } catch (_: android.content.ActivityNotFoundException) {
            message = "Voice input is unavailable on this device. Please type your answer."
        } catch (_: SecurityException) {
            message = "The speech service could not be opened. Please type your answer."
        }
    }, modifier = Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(16.dp)) { Text("🎙 $label") }
    Text("Uses your device's speech service, which may process audio online.", style = MaterialTheme.typography.bodySmall)
    message?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
}

@Composable
private fun MasteryScreen(state: AppUiState, onContinue: () -> Unit) = Page(modifier = Modifier.padding(top = 38.dp)) {
    RewriteAssessmentFeedback(state)
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFECFDF5)), shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(30.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("🏆", style = MaterialTheme.typography.displaySmall)
            Text("Great job!", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.ExtraBold, color = Success)
            Text("Concept mastered", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
        }
    }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Metric("Mastery score", "${state.masteryScore}%", Success); Metric("Coaching rounds", state.coachingRound.toString(), Indigo); Metric("AI confidence", state.masteryConfidence, Success)
        }
    }
    val chapters = chaptersBySubject[state.subject?.id].orEmpty()
    val currentIndex = chapters.indexOfFirst { it.id == state.masteryChapter?.id }
    val nextTitle = chapters.getOrNull(currentIndex + 1)?.title
    TipCard(if (nextTitle != null) "Next chapter unlocked" else "Learning path complete", if (nextTitle != null) "Keep your streak going with $nextTitle." else "You completed the available chapters in this subject.")
    PrimaryButton("Continue learning", onClick = onContinue)
}

@Composable
private fun RewriteAssessmentFeedback(state: AppUiState) {
    val points = state.assessmentPoints
    val feedback = state.assessmentFeedback
    if (points != null && !feedback.isNullOrBlank()) {
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Last explanation: $points / 4", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSecondaryContainer)
                Text(feedback, color = MaterialTheme.colorScheme.onSecondaryContainer)
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String, color: Color) = Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(label, color = Muted); Text(value, color = color, fontWeight = FontWeight.ExtraBold) }

@Composable
private fun ParentDashboard(state: AppUiState, onBack: () -> Unit) = Page {
    TextButton(onClick = onBack) { Text("‹ Back to subjects") }
    Header("Parent & teacher view", "Student progress", "A clear snapshot of learning progress and the best next action.")
    val snapshot = state.progressSnapshot
    if (snapshot != null) {
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("7-day learning report", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                Metric("Learning indicator", if (snapshot.questionsAnswered == 0) "Not enough evidence" else "${snapshot.examReadiness}% · ${snapshot.readinessLabel}", Success)
                Text("Uncalibrated heuristic, not a prediction of exam performance.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Metric("Learning responses", snapshot.questionsAnswered.toString(), Indigo)
                Text("Includes diagnostic answers, guided practice and explanations in the last 7 days (UTC).", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Metric("Response accuracy", if (snapshot.questionsAnswered == 0) "No responses yet" else "${snapshot.accuracy}%", Success)
                Metric("Unique chapters mastered", snapshot.masteredChapters.toString(), Indigo)
            }
        }
    }
    Text("Current assessed-chapter progress (not limited to this week)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    val displaySubjects = snapshot?.subjects?.map { (id, progress) -> id.replaceFirstChar(Char::uppercase) to progress } ?: emptyList()
    if (displaySubjects.isEmpty()) Text("No assessment yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
    displaySubjects.forEach { (subject, progress) ->
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(subject, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface); Text("$progress%", color = Success, fontWeight = FontWeight.Bold) }; LinearProgressIndicator(progress = { progress / 100f }, color = Success, trackColor = Color(0xFFE2E8F0), modifier = Modifier.fillMaxWidth()) } }
    }
    Header("Focus next", "Weak areas", snapshot?.weakAreas?.joinToString(" · ")?.ifBlank { "Complete a diagnostic to identify focus areas" } ?: "Complete a diagnostic to identify focus areas")
    TipCard("Suggested next step", snapshot?.recommendations?.joinToString("\n") ?: "Start a diagnostic to personalize your learning path.")
}

@Composable
private fun SettingsScreen(state: AppUiState, onBack: () -> Unit, onDarkMode: (Boolean) -> Unit, onGrade: () -> Unit, onSignOut: () -> Unit, onDelete: () -> Unit) {
    var confirmDelete by remember { mutableStateOf(false) }
    Page {
        TextButton(onClick = onBack) { Text("‹ Back to subjects") }
        Header("Preferences", "Settings and account", state.accountEmail.ifBlank { "Your private learner account" })
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.fillMaxWidth().padding(18.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                Column { Text("Dark mode", fontWeight = FontWeight.Bold); Text("Use a darker learning theme", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                Switch(checked = state.darkMode, onCheckedChange = onDarkMode)
            }
        }
        OutlinedButton(onClick = onGrade, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Text("Change grade · ${state.grade ?: "Not selected"}") }
        OutlinedButton(onClick = onSignOut, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Text("Sign out") }
        TextButton(onClick = { confirmDelete = true }, modifier = Modifier.fillMaxWidth()) { Text("Delete my account and learning data", color = MaterialTheme.colorScheme.error) }
    }
    if (confirmDelete) AlertDialog(onDismissRequest = { confirmDelete = false }, title = { Text("Delete account?") }, text = { Text("This permanently removes your account, documents, quizzes, and mastery history.") }, dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancel") } }, confirmButton = { TextButton(onClick = { confirmDelete = false; onDelete() }) { Text("Delete permanently", color = MaterialTheme.colorScheme.error) } })
}

@Composable
private fun TipCard(title: String, body: String) = Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF)), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) { Text(title, color = Blue, fontWeight = FontWeight.Bold); Text(body, color = Muted) } }

@Composable
private fun StudyMaterialScreen(loading: Boolean, onUpload: (android.content.Context, android.net.Uri) -> Unit, onBack: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> uri?.let { onUpload(context, it) } }
    Page {
        TextButton(onClick = onBack) { Text("‹ Back to learning path") }
        Header("Your study space", "Learn from your own material", "Upload a PDF, DOCX, or TXT file and receive source-grounded questions.")
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { Icon(Icons.Outlined.Description, null, tint = Indigo, modifier = Modifier.size(36.dp)); Text("Upload study material", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold); Text("Up to 50 MB. We detect chapters before generating a focused quiz.", color = MaterialTheme.colorScheme.onSurfaceVariant); PrimaryButton("Choose document", !loading) { picker.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain")) } } }
    }
}

@Composable
private fun DocumentChaptersScreen(state: AppUiState, onSelect: (String) -> Unit, onCreate: () -> Unit) {
    val document = state.document ?: return
    Page { Header("Study material", "Choose a chapter", "Select one section from ${document.name} for a ten-question session."); document.chapters.forEach { chapter -> AnswerChoice(chapter.title, state.selectedChapterId == chapter.id) { onSelect(chapter.id) } }; PrimaryButton("Generate 10 questions", state.selectedChapterId != null && !state.loading, onCreate) }
}

@Composable
private fun DocumentQuestionScreen(state: AppUiState, onAnswer: (String) -> Unit) {
    val question = state.question ?: return; var selected by remember(question.id) { mutableStateOf<String?>(null) }
    Page { Text("QUESTION ${question.ordinal} OF ${state.documentQuestionTotal}", color = Indigo, fontWeight = FontWeight.Bold); Text(question.prompt, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface); question.options.forEach { AnswerChoice(it, selected == it) { selected = it } }; Text("Source: ${question.sourceReference}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall); PrimaryButton("Check answer", selected != null && !state.loading) { selected?.let(onAnswer) } }
}

@Composable
private fun DocumentFeedbackScreen(feedback: Feedback?, onContinue: () -> Unit) {
    feedback ?: return; val color = if (feedback.correct) Success else Warning
    Page { Icon(if (feedback.correct) Icons.Outlined.CheckCircle else Icons.Outlined.ErrorOutline, null, tint = color, modifier = Modifier.size(48.dp)); Header("Study feedback", if (feedback.correct) "Correct!" else "Not quite", if (feedback.correct) "Nice work — keep building your streak." else "Your answer: ${feedback.selected}\nCorrect answer: ${feedback.answer}"); Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) { Text("Why", fontWeight = FontWeight.Bold); Text(feedback.explanation) } }; Text("Source: ${feedback.source}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall); PrimaryButton(if (feedback.next == null) "See results" else "Next question", onClick = onContinue) }
}

@Composable
private fun DocumentResultsScreen(results: Results?, onAgain: () -> Unit, onBack: () -> Unit) {
    results ?: return
    Page { Header("Session complete", "${results.correct} / ${results.total} correct", "Accuracy: ${(results.accuracy * 100).toInt()}%. Review missed concepts before moving on."); results.mistakes.forEach { mistake -> TipCard("Review question ${mistake.ordinal}", "${mistake.prompt}\nSource: ${mistake.sourceReference}") }; PrimaryButton("Study another document", onClick = onAgain); TextButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Return to learning path") } }
}

@Composable
private fun LoadingOverlay() = Box(Modifier.fillMaxSize().background(Color(0x990F172A)), contentAlignment = Alignment.Center) { Card(shape = RoundedCornerShape(20.dp)) { Row(Modifier.padding(24.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) { CircularProgressIndicator(); Text("Preparing your learning session…") } } }

@Composable
private fun ErrorDialog(message: String, onDismiss: () -> Unit) = AlertDialog(onDismissRequest = onDismiss, icon = { Icon(Icons.Outlined.ErrorOutline, null) }, title = { Text("We could not continue") }, text = { Text(message) }, confirmButton = { TextButton(onClick = onDismiss) { Text("Try again") } })
