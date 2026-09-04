package com.konetibalaji.learning

import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.enableEdgeToEdge
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.compose.LocalActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Checkbox
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.paneTitle
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.core.view.WindowCompat
import java.util.Base64

class MainActivity : ComponentActivity() {
    private val learningModel: LearningViewModel get() = androidx.lifecycle.ViewModelProvider(this)[LearningViewModel::class.java]
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); enableEdgeToEdge(); setContent { LearnSmartApp() } }
    override fun onResume() { super.onResume(); learningModel.studyActivityResumed(true) }
    override fun onPause() { learningModel.studyActivityResumed(false); super.onPause() }
    override fun onUserInteraction() { super.onUserInteraction(); learningModel.studyInteraction() }
}

private val Indigo: Color @Composable get() = MaterialTheme.colorScheme.primary
private val Blue: Color @Composable get() = MaterialTheme.colorScheme.secondary
private val Success: Color @Composable get() = MaterialTheme.colorScheme.tertiary
private val Warning: Color @Composable get() = MaterialTheme.colorScheme.error
private val Muted: Color @Composable get() = MaterialTheme.colorScheme.onSurfaceVariant

fun learningColorScheme(dark: Boolean) = if (dark) {
    darkColorScheme(primary = Color(0xFFA5B4FC), secondary = Color(0xFF93C5FD), tertiary = Color(0xFF6EE7B7))
} else {
    lightColorScheme(primary = Color(0xFF4F46E5), secondary = Color(0xFF2563EB), tertiary = Color(0xFF065F46),
        background = Color(0xFFF8FAFC), surface = Color.White)
}

@Composable
private fun LearnSmartApp(viewModel: LearningViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var teacherSpeaking by remember { mutableStateOf(false) }
    LaunchedEffect(state.screen) {
        if (state.screen !in setOf(Screen.Tutor, Screen.TutorChat)) teacherSpeaking = false
    }
    val colors = learningColorScheme(state.darkMode)
    val activity = LocalActivity.current
    val auditExport = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if (uri != null) activity?.let { viewModel.exportGuardianAccessHistory(it.contentResolver, uri) }
    }
    SideEffect {
        activity?.let {
            WindowCompat.getInsetsController(it.window, it.window.decorView).apply {
                isAppearanceLightStatusBars = !state.darkMode
                isAppearanceLightNavigationBars = !state.darkMode
            }
        }
    }
    MaterialTheme(colorScheme = colors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Scaffold(
                containerColor = MaterialTheme.colorScheme.background,
                topBar = { PersistentTeacherBar(tutorPresence(state.loading, teacherSpeaking), state.accountEmail.isNotBlank()) },
            ) { padding ->
                Box(Modifier.fillMaxSize().padding(padding)) {
                    when (state.screen) {
                        Screen.SignIn -> SignInScreen(state.loading, viewModel::authenticate) {
                            activity?.let { viewModel.authenticateGoogle { nonce -> requestGoogleIdToken(it, nonce) } }
                        }
                        Screen.Grade -> GradeScreen(viewModel::selectGrade)
                        Screen.Subjects -> SubjectsScreen(state, viewModel::selectSubject, viewModel::openParentDashboard, viewModel::openGuardianAccess, viewModel::startDocumentStudy, viewModel::openSettings, viewModel::resumeLearning, viewModel::resumeDocumentQuiz, viewModel::refreshProgress)
                        Screen.MasteryChapters -> ChapterScreen(state, viewModel::selectMasteryChapter, viewModel::backToSubjects, viewModel::refreshProgress)
                        Screen.Diagnostic -> DiagnosticScreen(state, viewModel::selectDiagnosticAnswer, viewModel::submitDiagnostic)
                        Screen.Tutor -> TutorScreen(state, viewModel::startPractice, viewModel::openTutorConversation) { teacherSpeaking = it }
                        Screen.TutorChat -> TutorConversationScreen(state, viewModel::changeTutorQuestion, viewModel::sendTutorQuestion, viewModel::backFromTutorConversation) { teacherSpeaking = it }
                        Screen.Practice -> PracticeScreen(state, viewModel::showHint, viewModel::checkPractice, viewModel::moveToRewrite)
                        Screen.Rewrite -> RewriteScreen(state, viewModel::updateRewrite, viewModel::submitRewrite)
                        Screen.Mastery -> MasteryScreen(state, viewModel::continueFromMastery)
                        Screen.ParentDashboard -> ParentDashboard(state, viewModel::backFromParentDashboard)
                        Screen.GuardianAccess -> GuardianAccessScreen(state, viewModel::updateGuardianCode, viewModel::redeemGuardianCode, viewModel::createGuardianInvitation, viewModel::openLinkedLearnerReport, viewModel::unlinkLearner, viewModel::revokeGuardian, viewModel::refreshGuardianAccess, { auditExport.launch("report-access-history.csv") }, viewModel::backToSubjects)
                        Screen.Home -> StudyMaterialScreen(state.loading, viewModel::upload, viewModel::backToSubjects, viewModel::openDocumentLibrary)
                        Screen.DocumentLibrary -> DocumentLibraryScreen(state, viewModel::openSavedDocument, viewModel::deleteDocument, viewModel::refreshDocumentLibrary, viewModel::startDocumentStudy)
                        Screen.Chapters -> DocumentChaptersScreen(state, viewModel::selectChapter, viewModel::createQuiz, viewModel::startDocumentStudy, viewModel::selectAllDocumentChapters, viewModel::clearDocumentChapters, viewModel::setDocumentQuestionCount, viewModel::setDocumentDifficulty, viewModel::setDocumentQuestionType, viewModel::repairDocumentStructure, { viewModel.previewDocumentChapter(it) }, viewModel::setSourceQuery, viewModel::searchDocumentSource, viewModel::useSourceSearchResult, viewModel::loadPdfPages, viewModel::setPdfPageInput, viewModel::reviewPdfPages, viewModel::confirmPdfPages)
                        Screen.DocumentPreview -> DocumentPreviewScreen(state, viewModel::closeDocumentPreview, viewModel::changePreviewPage, viewModel::addDocumentExcerpt)
                        Screen.Question -> DocumentQuestionScreen(state, viewModel::submitAnswer)
                        Screen.Feedback -> DocumentFeedbackScreen(state, viewModel::viewQuestionSource, viewModel::continueAfterFeedback)
                        Screen.Results -> DocumentResultsScreen(state.results, viewModel::viewQuestionSource, viewModel::retryDocumentMistakes, { viewModel.configureAnotherDocumentQuiz() }, { viewModel.configureAnotherDocumentQuiz(true) }, viewModel::startAnotherDocument, viewModel::backToSubjects, state.savedQuizDifficulty, state.savedQuizQuestionType, state.loading)
                        Screen.Settings -> SettingsScreen(state, viewModel::backToSubjects, viewModel::setDarkMode, viewModel::changeGrade, viewModel::signOut, viewModel::deleteAccount, viewModel::openInterests)
                        Screen.Interests -> InterestsScreen(state, viewModel::selectInterest, viewModel::clearInterests, viewModel::saveInterests, viewModel::reloadInterests, viewModel::openSettings)
                    }
                    if (state.loading) LoadingOverlay(state.uploadProgress)
                }
            }
        }
        state.error?.let { ErrorDialog(it, viewModel::clearError) }
        state.questionSourceEvidence?.let { SourceEvidenceDialog(it, viewModel::closeQuestionSource) }
    }
}

@Composable
private fun PersistentTeacherBar(presence: TutorPresence, signedIn: Boolean) {
    val description = if (!signedIn) "AI teacher available after sign in" else when (presence) {
        TutorPresence.READY -> "AI teacher ready"
        TutorPresence.THINKING -> "AI teacher is thinking"
        TutorPresence.SPEAKING -> "AI teacher is speaking"
    }
    Surface(color = MaterialTheme.colorScheme.surface, tonalElevation = 3.dp) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 52.dp).padding(horizontal = 20.dp, vertical = 8.dp)
                .semantics { contentDescription = description; liveRegion = LiveRegionMode.Polite },
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = RoundedCornerShape(50), modifier = Modifier.size(36.dp)) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(Icons.Outlined.School, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(23.dp))
                }
            }
            Text(
                if (!signedIn) "AI Teacher • Sign in to begin" else when (presence) {
                    TutorPresence.READY -> "AI Teacher • Ready"
                    TutorPresence.THINKING -> "AI Teacher • Thinking"
                    TutorPresence.SPEAKING -> "AI Teacher • Speaking"
                },
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.labelLarge,
            )
            Spacer(Modifier.weight(1f))
            if (presence == TutorPresence.THINKING) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
        }
    }
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
    onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp), shape = RoundedCornerShape(16.dp),
    colors = ButtonDefaults.buttonColors(containerColor = Indigo),
) { Text(label, fontWeight = FontWeight.Bold) }

@Composable
private fun SignInScreen(loading: Boolean, onAuthenticate: (String, String, Boolean) -> Unit, onGoogleSignIn: () -> Unit) {
    var email by remember { mutableStateOf("") }; var password by remember { mutableStateOf("") }; var createAccount by remember { mutableStateOf(false) }
    Page(modifier = Modifier.padding(top = 22.dp)) {
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("✦", style = MaterialTheme.typography.displayMedium, color = Indigo)
                Text("LEARN SMART AI", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold, color = Indigo)
                Text("Your personal learning coach", color = Muted)
            }
        }
        Header(if (createAccount) "New learner" else "Welcome back", if (createAccount) "Create your account." else "Learn at your pace.", "Discover what you know, practise what you need, and master every concept.")
        OutlinedTextField(email, { email = it }, Modifier.fillMaxWidth(), enabled = !loading, label = { Text("Email") }, singleLine = true, shape = RoundedCornerShape(14.dp))
        OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), enabled = !loading, label = { Text("Password") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), supportingText = { Text("At least 12 characters") }, shape = RoundedCornerShape(14.dp))
        PrimaryButton(if (createAccount) "Create account" else "Sign in", !loading && email.isNotBlank() && password.length >= 12) { onAuthenticate(email.trim(), password, createAccount) }
        TextButton(onClick = { createAccount = !createAccount }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text(if (createAccount) "Already have an account? Sign in" else "New student? Create a private account") }
        OutlinedButton(onClick = onGoogleSignIn, enabled = !loading && BuildConfig.GOOGLE_SERVER_CLIENT_ID.isNotEmpty(), modifier = Modifier.fillMaxWidth().heightIn(min = 54.dp)) {
            Text("Sign in with Google")
        }
        if (BuildConfig.GOOGLE_SERVER_CLIENT_ID.isEmpty()) Text("Google sign-in is not configured for this build. Use email sign-in.", color = Muted)
    }
}

@Composable
private fun GradeScreen(onSelect: (Int) -> Unit) = Page {
    Text("👋 Hello, learner", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
    Header("Your learning path", "Select your grade", "We use your grade to explain concepts at the right level.")
    AccessibleSelectionGrid((1..12).toList(), 96f, 3) { grade ->
        Card(modifier = Modifier.fillMaxWidth().heightIn(min = 84.dp).clickable { onSelect(grade) }, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
            Box(Modifier.fillMaxWidth().heightIn(min = 84.dp).padding(12.dp), contentAlignment = Alignment.Center) { Text("Grade\n$grade", textAlign = TextAlign.Center, fontWeight = FontWeight.Bold, color = Indigo) }
        }
    }
    TipCard("You can change this later", "Your tutor adapts each explanation as you grow.")
}

@Composable
private fun SubjectsScreen(state: AppUiState, onSelect: (LearningSubject) -> Unit, onParent: () -> Unit, onGuardian: () -> Unit, onDocuments: () -> Unit, onSettings: () -> Unit, onResume: () -> Unit, onResumeDocument: () -> Unit, onRefresh: () -> Unit) = Page {
    Header("Grade ${state.grade ?: 6}", "What would you like to learn?", "Pick a subject to continue your personalised path.")
    if (state.canResumeMastery) PrimaryButton("Resume saved learning", !state.loading, onResume)
    if (state.canResumeDocumentQuiz) PrimaryButton("Resume document study", !state.loading, onResumeDocument)
    AccessibleSelectionGrid(state.catalogSubjects, 160f, 2) { subject ->
        val progress = state.progressSnapshot?.subjects?.get(subject.id)
        Card(modifier = Modifier.fillMaxWidth().heightIn(min = 178.dp).clickable { onSelect(subject) }, colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(22.dp), elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(subject.icon, style = MaterialTheme.typography.headlineLarge, color = Indigo)
                Text(subject.title, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                LinearProgressIndicator(progress = { (progress ?: 0) / 100f }, modifier = Modifier.fillMaxWidth(), color = Success, trackColor = Color(0xFFE2E8F0))
                Text(if (progress == null) "No assessment yet" else "$progress% assessed progress", color = Muted, style = MaterialTheme.typography.labelMedium)
            }
        }
    }
    if (!state.loading && state.catalogSubjects.isEmpty()) {
        Text("The curriculum catalog is unavailable. Reconnect, then refresh.", color = MaterialTheme.colorScheme.error)
        PrimaryButton("Refresh curriculum and progress", onClick = onRefresh)
    }
    state.catalogVersion?.let { Text("Catalog $it · Board alignment ${state.catalogBoard ?: "unconfirmed"}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
    state.progressSnapshot?.badges?.takeIf { it.isNotEmpty() }?.let { badges ->
        Text("Earned badges", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        badges.forEach { badge ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth().semantics {
                    contentDescription = "Earned badge: ${badge.title}. ${badge.description}"
                }) {
                Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("★", color = Warning, style = MaterialTheme.typography.headlineSmall)
                    Column { Text(badge.title, fontWeight = FontWeight.Bold); Text(badge.description, style = MaterialTheme.typography.bodySmall) }
                }
            }
        }
    }
    OutlinedButton(onClick = onParent, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(16.dp)) { Text("View my progress report") }
    OutlinedButton(onClick = onGuardian, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(16.dp)) { Text("Parent & teacher access") }
    TextButton(onClick = onDocuments, modifier = Modifier.fillMaxWidth()) { Text("Study from my own document") }
    TextButton(onClick = onSettings, modifier = Modifier.fillMaxWidth()) { Text("Settings and account") }
}

@Composable
private fun ChapterScreen(state: AppUiState, onSelect: (MasteryChapter) -> Unit, onBack: () -> Unit, onRefresh: () -> Unit) = Page {
    TextButton(onClick = onRefresh, enabled = !state.loading) { Text("Refresh progress") }
    TextButton(onClick = onBack) { Text("‹ All subjects") }
    Header(state.subject?.title ?: "Mathematics", "Choose a chapter", "Master a concept to unlock what comes next.")
    (state.catalogChapters[state.subject?.id] ?: emptyList()).forEach { chapter ->
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
private fun TutorScreen(state: AppUiState, onUnderstand: () -> Unit, onAsk: () -> Unit, onSpeakingChanged: (Boolean) -> Unit) {
    val lesson = state.tutorLesson ?: TutorLesson(
        "Add the numerators",
        "When fractions have the same denominator, the pieces are the same size. Keep the denominator and add only the top numbers.",
        "3/4 + 1/4 = (3 + 1) / 4 = 4/4 = 1",
        "Try this pattern: 2/5 + 3/5 = 5/5 = 1",
        "What is 2/8 + 4/8?",
    )
    var reading by remember(lesson) { mutableStateOf(false) }
    Page {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("✦ AI Teacher", color = Warning, fontWeight = FontWeight.Bold)
            Text("Not quite — let’s build it together.", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Your answer: ${state.selectedDiagnosticAnswer ?: "Needs another look"}", color = Muted)
        }
    }
    RewriteAssessmentFeedback(state)
    LessonWalkthrough(lesson)
    TipCard("Your tutor is paying attention", if (state.coachingRound > 0) "Let’s try a different explanation and practise it once more." else "A short practice question will check that the idea clicked.")
    TutorAvatar(tutorPresence(state.loading, reading))
    ReadAloudControls(listOf(lesson.title, lesson.explanation, lesson.workedExample).joinToString(". ")) {
        reading = it
        onSpeakingChanged(it)
    }
    OutlinedButton(onClick = onAsk, modifier = Modifier.fillMaxWidth()) { Text("Ask the tutor a question") }
    InteractiveLessonExplorer(state.subject?.id, state.masteryChapter?.id)
    PrimaryButton("I understand — practise now", onClick = onUnderstand)
    }
}

@Composable
private fun TutorConversationScreen(state: AppUiState, onChange: (String) -> Unit, onSend: () -> Unit, onBack: () -> Unit, onSpeakingChanged: (Boolean) -> Unit) {
    var reading by remember(state.masterySessionId) { mutableStateOf(false) }
    Page {
    BackHandler(enabled = !state.loading, onBack = onBack)
    TutorAvatar(tutorPresence(state.loading, reading))
    Header("Ask about this lesson", "Talk with your tutor", "Questions and replies are saved with this learning session. They do not change your score.")
    Text("Your question and recent lesson conversation are sent to the AI service. Do not include private information. AI replies can be wrong.", style = MaterialTheme.typography.bodySmall)
    if (state.tutorTurns.isEmpty()) Text("No questions in this lesson conversation yet.")
    for (turn in state.tutorTurns) {
        Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("You: ${turn.question}", fontWeight = FontWeight.Bold)
            when (turn.status) {
                "complete" -> {
                    if (turn.supported == false) Text("The tutor needs clarification or could not answer from this lesson.")
                    Text(requireNotNull(turn.answer))
                }
                "pending" -> Text("Reply pending. Use Check reply; do not send the question again as a new request.")
                "failed" -> {
                    Text("The tutor could not reply. Retry only when you are ready; it counts as a new request.")
                    OutlinedButton(onClick = { onChange(turn.question) }, enabled = !state.loading && state.pendingTutorQuestion == null) {
                        Text("Use this question again")
                    }
                }
            }
        } }
    }
    state.tutorTurns.lastOrNull { it.status == "complete" }?.answer?.let { answer ->
        ReadAloudControls(answer) {
            reading = it
            onSpeakingChanged(it)
        }
    }
    if (state.pendingTutorQuestion == null) {
        OutlinedTextField(state.tutorQuestion, onChange, modifier = Modifier.fillMaxWidth(), label = { Text("My question (up to 1000 characters)") })
        VoiceInputButton("Speak my tutor question") { onChange(listOf(state.tutorQuestion, it).filter(String::isNotBlank).joinToString(" ")) }
        PrimaryButton("Send question", state.tutorQuestion.isNotBlank() && !state.loading, onSend)
    } else {
        Text("Pending question: ${state.pendingTutorQuestion.question}")
        Text("If a response was interrupted, Check reply safely reuses the same request. A stalled request may take up to three minutes to resolve.")
        PrimaryButton("Check reply", !state.loading, onSend)
    }
    OutlinedButton(onClick = onBack, enabled = !state.loading, modifier = Modifier.fillMaxWidth()) { Text("Back to lesson") }
    }
}

@Composable
private fun TutorAvatar(presence: TutorPresence) {
    val transition = rememberInfiniteTransition(label = "AI teacher activity")
    val activity by transition.animateFloat(
        initialValue = 0f,
        targetValue = if (presence == TutorPresence.READY) 0f else 1f,
        animationSpec = infiniteRepeatable(tween(420), RepeatMode.Reverse),
        label = "AI teacher speaking or thinking",
    )
    val primary = MaterialTheme.colorScheme.primary
    val container = MaterialTheme.colorScheme.primaryContainer
    val ink = MaterialTheme.colorScheme.onPrimaryContainer
    val description = when (presence) {
        TutorPresence.READY -> "AI teacher ready"
        TutorPresence.THINKING -> "AI teacher is thinking"
        TutorPresence.SPEAKING -> "AI teacher is speaking"
    }
    Card(
        modifier = Modifier.fillMaxWidth().semantics { contentDescription = description },
        colors = CardDefaults.cardColors(containerColor = container),
        shape = RoundedCornerShape(22.dp),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Canvas(
                Modifier.size(68.dp).graphicsLayer {
                    val animatedScale = if (presence == TutorPresence.THINKING) 1f + activity * 0.05f else 1f
                    scaleX = animatedScale
                    scaleY = animatedScale
                }
            ) {
                drawCircle(primary)
                drawCircle(container, radius = size.minDimension * 0.39f)
                val eyeY = size.height * 0.42f
                drawCircle(ink, radius = size.minDimension * 0.045f, center = androidx.compose.ui.geometry.Offset(size.width * 0.38f, eyeY))
                drawCircle(ink, radius = size.minDimension * 0.045f, center = androidx.compose.ui.geometry.Offset(size.width * 0.62f, eyeY))
                val mouthHalfHeight = size.height * if (presence == TutorPresence.SPEAKING) (0.025f + activity * 0.06f) else 0.015f
                drawLine(
                    color = ink,
                    start = androidx.compose.ui.geometry.Offset(size.width * 0.38f, size.height * 0.64f - mouthHalfHeight),
                    end = androidx.compose.ui.geometry.Offset(size.width * 0.62f, size.height * 0.64f + mouthHalfHeight),
                    strokeWidth = size.minDimension * 0.055f,
                    cap = StrokeCap.Round,
                )
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("AI Teacher", fontWeight = FontWeight.Bold, color = ink)
                Text(
                    when (presence) {
                        TutorPresence.READY -> "Ready when you are"
                        TutorPresence.THINKING -> "Thinking about your lesson"
                        TutorPresence.SPEAKING -> "Speaking the explanation"
                    },
                    color = ink,
                )
            }
        }
    }
}

@Composable
private fun PracticeScreen(state: AppUiState, onHint: () -> Unit, onCheck: (String) -> Unit, onContinue: () -> Unit) {
    var answer by remember(state.masterySessionId, state.tutorLesson?.practicePrompt) { mutableStateOf("") }
    Page {
        Header("Practice with AI", "Let’s try together.", "Apply the idea from the tutor's explanation.")
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(20.dp), modifier = Modifier.fillMaxWidth()) { Text(state.tutorLesson?.practicePrompt ?: "What is 2/8 + 4/8?", modifier = Modifier.padding(22.dp), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface) }
        OutlinedTextField(answer, { answer = it }, Modifier.fillMaxWidth(), label = { Text("Your answer") }, placeholder = { Text("Type a short answer") }, singleLine = true, shape = RoundedCornerShape(14.dp))
        VoiceInputButton("Speak my answer") { answer = it }
        if (state.showHint) TipCard("Hint", state.tutorLesson?.hint ?: "Review the tutor explanation, then try again.")
        when (state.practiceResult) {
            true -> Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer), shape = RoundedCornerShape(16.dp)) { Text("Correct! You are ready to explain the idea.", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onTertiaryContainer, fontWeight = FontWeight.Bold) }
            false -> Text("Not quite. Review the question shown above and use its hint before answering.", color = Warning, fontWeight = FontWeight.Medium)
            null -> Unit
        }
        if (state.practiceResult == true) PrimaryButton("Explain it in your own words", onClick = onContinue)
        else { OutlinedButton(onClick = onHint, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(16.dp)) { Text("Show hint") }; PrimaryButton("Check answer", answer.isNotBlank()) { onCheck(answer) } }
    }
}

@Composable
private fun RewriteScreen(state: AppUiState, onChange: (String) -> Unit, onSubmit: () -> Unit) = Page {
    Header("Show your thinking", "Explain it in your own words", "Explain ${state.tutorLesson?.title ?: "the concept"} and connect it to the practice example.")
    OutlinedTextField(state.rewrite, onChange, modifier = Modifier.fillMaxWidth().heightIn(min = 190.dp), label = { Text("My explanation") }, placeholder = { Text("I know this equals 1 because…") }, shape = RoundedCornerShape(16.dp))
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
    }, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(16.dp)) { Text("🎙 $label") }
    Text("Uses your device's speech service, which may process audio online.", style = MaterialTheme.typography.bodySmall)
    message?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
}

@Composable
private fun MasteryScreen(state: AppUiState, onContinue: () -> Unit) = Page(modifier = Modifier.padding(top = 38.dp)) {
    RewriteAssessmentFeedback(state)
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
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
    val chapters = state.catalogChapters[state.subject?.id].orEmpty()
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
    TextButton(onClick = onBack) { Text(if (state.reportAccountEmail == null) "‹ Back to subjects" else "‹ Back to linked learners") }
    Header("Read-only progress report", if (state.reportAccountEmail == null) "My progress" else "Student progress",
        if (state.reportAccountEmail == null) "A clear snapshot of your learning progress and the best next action." else "Shared aggregate progress only. Answers and uploaded documents are never included.")
    state.reportAccountEmail?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface) }
    val snapshot = state.progressSnapshot
    if (snapshot != null) {
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("7-day learning report", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                Metric("Learning indicator", learningIndicatorText(snapshot.examReadiness, snapshot.readinessLabel), Success)
                Text("Requires at least 10 independent diagnostic or rewrite answers across 2 chapters. Uncalibrated heuristic, not a prediction of exam performance.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Metric("Learning responses", snapshot.questionsAnswered.toString(), Indigo)
                Text("Includes diagnostic answers, guided practice and explanations in the last 7 days (UTC).", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Metric("Response accuracy", if (snapshot.questionsAnswered == 0) "No responses yet" else "${snapshot.accuracy}%", Success)
                Metric("Unique chapters mastered", snapshot.masteredChapters.toString(), Indigo)
                Metric("Recorded study presence", weeklyStudyTimeLabel(snapshot.weeklyObservedStudySeconds), Indigo)
                Text("Last 7 days, selected grade. Counts recorded activity on learning screens only, not total study time or proof of attention. Idle, offline and older untracked activity may be missing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
    Text("Current assessed-chapter progress (not limited to this week)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    val displaySubjects = snapshot?.subjects?.map { (id, progress) -> id.replaceFirstChar(Char::uppercase) to progress } ?: emptyList()
    if (displaySubjects.isEmpty()) Text("No assessment yet", color = MaterialTheme.colorScheme.onSurfaceVariant)
    displaySubjects.forEach { (subject, progress) ->
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(subject, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface); Text("$progress%", color = Success, fontWeight = FontWeight.Bold) }; LinearProgressIndicator(progress = { progress / 100f }, color = Success, trackColor = Color(0xFFE2E8F0), modifier = Modifier.fillMaxWidth()) } }
    }
    Header("Focus next", "Current weak areas", snapshot?.weakAreas?.joinToString(" · ")?.ifBlank { "No unresolved weak areas recorded. Continue assessing and practising." } ?: "Complete a diagnostic to identify focus areas")
    TipCard("Suggested next step", snapshot?.recommendations?.joinToString("\n") ?: "Start a diagnostic to personalize your learning path.")
}

internal fun learningIndicatorText(examReadiness: Int, readinessLabel: String): String =
    if (readinessLabel == "Insufficient evidence") "Not enough evidence"
    else "$examReadiness% · $readinessLabel"

@Composable
private fun GuardianAccessScreen(state: AppUiState, onCode: (String) -> Unit, onRedeem: () -> Unit,
                                 onInvite: () -> Unit, onView: (GuardianAccount) -> Unit,
                                 onUnlink: (String) -> Unit, onRevoke: (String) -> Unit,
                                 onRefresh: () -> Unit, onExport: () -> Unit,
                                 onBack: () -> Unit) = Page {
    TextButton(onClick = onBack) { Text("‹ Back to subjects") }
    Header("Consent and privacy", "Parent & teacher access", "Link a separate account to share aggregate progress. Answers, tutor conversations and uploaded documents stay private.")
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Link a learner report", fontWeight = FontWeight.Bold)
            OutlinedTextField(value = state.guardianCodeDraft, onValueChange = onCode, modifier = Modifier.fillMaxWidth(),
                label = { Text("Single-use learner code") }, singleLine = true)
            PrimaryButton("Link learner", state.guardianCodeDraft.length >= 20 && !state.loading, onRedeem)
        }
    }
    Text("Linked learner reports", fontWeight = FontWeight.Bold)
    when {
        state.linkedLearners == null -> Text("Loading linked learners…", color = MaterialTheme.colorScheme.onSurfaceVariant)
        state.linkedLearners.isEmpty() -> Text("No learner reports linked.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        else -> state.linkedLearners.forEach { learner ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(learner.email, fontWeight = FontWeight.Bold)
                    OutlinedButton(onClick = { onView(learner) }, modifier = Modifier.fillMaxWidth()) { Text("View Grade ${state.grade ?: 8} report") }
                    TextButton(onClick = { onUnlink(learner.id) }, modifier = Modifier.fillMaxWidth()) { Text("Remove linked learner", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Share my report", fontWeight = FontWeight.Bold)
            Text("Create a 15-minute single-use code. Creating another code immediately invalidates the previous one.")
            PrimaryButton("Create sharing code", !state.loading, onInvite)
            state.guardianInvitationCode?.let {
                Text(it, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text("Give this code directly to the parent or teacher. It is shown only in this session and cannot be recovered.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
    Text("Accounts that can view my report", fontWeight = FontWeight.Bold)
    when {
        state.linkedGuardians == null -> Text("Loading access list…", color = MaterialTheme.colorScheme.onSurfaceVariant)
        state.linkedGuardians.isEmpty() -> Text("No parent or teacher account has access.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        else -> state.linkedGuardians.forEach { guardian ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text(guardian.email, fontWeight = FontWeight.Bold)
                    TextButton(onClick = { onRevoke(guardian.id) }, modifier = Modifier.fillMaxWidth()) { Text("Revoke report access", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
    Text("My report access history", fontWeight = FontWeight.Bold)
    Text("This record shows grants and revocations for your report. Deleted accounts are not identified.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    when {
        state.guardianAccessHistory == null -> Text("Loading access history…", color = MaterialTheme.colorScheme.onSurfaceVariant)
        state.guardianAccessHistory.isEmpty() -> Text("No report access changes recorded.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        else -> state.guardianAccessHistory.asReversed().forEach { event ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(guardianAccessEventDescription(event.eventType), fontWeight = FontWeight.Bold)
                    Text(guardianAccessAccountLabel(event), color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Text(guardianAccessOccurredLabel(event.occurredAt), style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
    OutlinedButton(onClick = onExport, enabled = !state.loading,
        modifier = Modifier.fillMaxWidth()) { Text("Save access history CSV") }
    Text("You choose where to save it. The export contains access timestamps, changes, and account labels, but no internal account IDs.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    TextButton(onClick = onRefresh, enabled = !state.loading, modifier = Modifier.fillMaxWidth()) { Text("Refresh access list") }
}

@Composable
private fun SettingsScreen(state: AppUiState, onBack: () -> Unit, onDarkMode: (Boolean) -> Unit, onGrade: () -> Unit, onSignOut: () -> Unit, onDelete: () -> Unit, onInterests: () -> Unit) {
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
        OutlinedButton(onClick = onGrade, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp), shape = RoundedCornerShape(16.dp)) { Text("Change grade · ${state.grade ?: "Not selected"}") }
        OutlinedButton(onClick = onInterests, modifier = Modifier.fillMaxWidth()) { Text("Learning interests") }
        state.retentionPolicy?.let { policy ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("Your data retention", fontWeight = FontWeight.Bold)
                    Text("Learning history stays until you delete your account.")
                    Text("Uploaded documents stay until you delete the document or your account.")
                    Text("Deleted files are queued for immediate cleanup. Untracked crash files are removed after ${policy.crashOrphanHours} hours.")
                    Text("Expired guardian invitations are removed after ${policy.guardianInvitationDays} days. Service backups expire after ${policy.backupDays} days.")
                }
            }
        }
        OutlinedButton(onClick = onSignOut, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp), shape = RoundedCornerShape(16.dp)) { Text("Sign out") }
        TextButton(onClick = { confirmDelete = true }, modifier = Modifier.fillMaxWidth()) { Text("Delete my account and learning data", color = MaterialTheme.colorScheme.error) }
    }
    if (confirmDelete) AlertDialog(onDismissRequest = { confirmDelete = false }, title = { Text("Delete account?") }, text = { Text("This permanently removes your account, documents, quizzes, and mastery history.") }, dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text("Cancel") } }, confirmButton = { TextButton(onClick = { confirmDelete = false; onDelete() }) { Text("Delete permanently", color = MaterialTheme.colorScheme.error) } })
}

@Composable
private fun InterestsScreen(state: AppUiState, onToggle: (String) -> Unit, onClear: () -> Unit, onSave: () -> Unit, onReload: () -> Unit, onBack: () -> Unit) = Page {
    TextButton(onClick = onBack, enabled = !state.loading) { Text("‹ Back to settings") }
    Header("Optional personalization", "Learning interests", "Choose up to three interests, or leave them empty.")
    Text("Saved choices are sent to the AI provider for new tutor explanations. They do not affect grading. Existing explanations stay unchanged.", color = MaterialTheme.colorScheme.onSurfaceVariant)
    if (state.savedInterests == null) {
        if (!state.loading) {
            Text("Interests could not be loaded. Your saved choices have not been changed.")
            OutlinedButton(onClick = onReload) { Text("Reload interests") }
        }
    } else {
        Text("${state.interestDraft.size} of 3 selected", fontWeight = FontWeight.Bold)
        availableInterests.forEach { interest ->
            val selected = interest in state.interestDraft
            OutlinedButton(onClick = { onToggle(interest) }, enabled = !state.loading && (selected || state.interestDraft.size < 3), modifier = Modifier.fillMaxWidth()) {
                Text("${if (selected) "Remove" else "Select"} ${interest.replaceFirstChar(Char::uppercase)}")
            }
        }
        TextButton(onClick = onClear, enabled = !state.loading) { Text("Clear all choices") }
        Text("Clear all choices and save to stop using interests. Leaving without saving discards your changes.", style = MaterialTheme.typography.bodySmall)
        PrimaryButton("Save interests", !state.loading && state.interestDraft != state.savedInterests, onSave)
        state.interestSaveMessage?.let { Text(it, color = MaterialTheme.colorScheme.tertiary) }
    }
}

@Composable
private fun TipCard(title: String, body: String) = Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) { Text(title, color = MaterialTheme.colorScheme.onSecondaryContainer, fontWeight = FontWeight.Bold); Text(body, color = MaterialTheme.colorScheme.onSecondaryContainer) } }

@Composable
private fun StudyMaterialScreen(loading: Boolean, onUpload: (android.content.Context, android.net.Uri) -> Unit, onBack: () -> Unit, onLibrary: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> uri?.let { onUpload(context, it) } }
    Page {
        TextButton(onClick = onBack, enabled = !loading) { Text("‹ Back to learning path") }
        Header("Your study space", "Learn from your own material", "Upload a PDF, DOCX, or TXT file and receive source-grounded questions.")
        OutlinedButton(onClick = onLibrary, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("My uploaded documents") }
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { Icon(Icons.Outlined.Description, null, tint = Indigo, modifier = Modifier.size(36.dp)); Text("Upload study material", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold); Text("Up to 50 MB. We detect chapters before generating a focused quiz.", color = MaterialTheme.colorScheme.onSurfaceVariant); PrimaryButton("Choose document", !loading) { picker.launch(arrayOf("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain")) } } }
    }
}

@Composable
private fun DocumentLibraryScreen(state: AppUiState, onOpen: (String) -> Unit, onDelete: (String) -> Unit, onRefresh: () -> Unit, onBack: () -> Unit) {
    var pendingDeletion by remember { mutableStateOf<StudyDocument?>(null) }
    Page {
    TextButton(onClick = onBack, enabled = !state.loading) { Text("‹ Back to study space") }
    Header("Your library", "Uploaded documents", "Open saved material to select a chapter and start a new quiz. Your existing quizzes are not deleted.")
    OutlinedButton(onClick = onRefresh, enabled = !state.loading) { Text("Refresh documents") }
    when {
        state.documentLibrary == null && !state.loading -> Text("Documents could not be loaded. Check your connection and refresh.")
        state.documentLibrary?.isEmpty() == true -> Text("No uploaded documents yet. Return to your study space to upload one.")
        else -> state.documentLibrary.orEmpty().forEach { document ->
            Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(document.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("${document.chapters.size} detected sections", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedButton(onClick = { onOpen(document.id) }, enabled = !state.loading) { Text("Open ${document.name}") }
                    TextButton(onClick = { pendingDeletion = document }, enabled = !state.loading) { Text("Delete ${document.name}", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
    }
    pendingDeletion?.let { document ->
        AlertDialog(onDismissRequest = { pendingDeletion = null },
            title = { Text("Delete this document?") },
            text = { Text("Permanently delete ${document.name} and all quizzes and answers created from it? This cannot be undone.") },
            dismissButton = { TextButton(onClick = { pendingDeletion = null }) { Text("Cancel") } },
            confirmButton = { TextButton(onClick = { pendingDeletion = null; onDelete(document.id) }) { Text("Delete document permanently", color = MaterialTheme.colorScheme.error) } })
    }
}

@Composable
private fun DocumentChaptersScreen(state: AppUiState, onSelect: (String) -> Unit, onCreate: () -> Unit, onBack: () -> Unit, onAll: () -> Unit, onClear: () -> Unit, onCount: (String) -> Unit, onDifficulty: (String) -> Unit, onType: (String) -> Unit, onRepair: () -> Unit, onPreview: (String) -> Unit, onQuery: (String) -> Unit, onSearch: () -> Unit, onUseResult: (Int) -> Unit, onLoadPages: () -> Unit, onPageInput: (Boolean, String) -> Unit, onReviewPages: () -> Unit, onConfirmPages: () -> Unit) {
    val document = state.document ?: return
    Page {
        TextButton(onClick = onBack, enabled = !state.loading) { Text("‹ Back to study space") }
        Header("Study material", "Choose chapters", "Select one or more chapters from ${document.name} and configure your quiz.")
        state.documentProgress?.let { progress ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Progress for this document", fontWeight = FontWeight.Bold)
                    Text("${progress.quizzesCompleted} completed quizzes • ${progress.questionsAnswered} answers • ${(progress.accuracy * 100).toInt()}% accuracy")
                    val trendText = when (progress.trend) {
                        "improving" -> "Improving by ${progress.improvementPercentagePoints?.toInt()} percentage points since your previous completed quiz"
                        "declining" -> "Down ${kotlin.math.abs(progress.improvementPercentagePoints?.toInt() ?: 0)} percentage points since your previous completed quiz"
                        "steady" -> "Accuracy is steady since your previous completed quiz"
                        else -> "Complete two quizzes to see your improvement trend"
                    }
                    Text(trendText, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (progress.chapters.isNotEmpty()) {
                        Text("Chapter accuracy", fontWeight = FontWeight.SemiBold)
                        progress.chapters.forEach { chapter ->
                            Text(if (chapter.accuracy == null) "${chapter.title} • Not started"
                                else "${chapter.title} • ${(chapter.accuracy * 100).toInt()}% accuracy from ${chapter.questionsAnswered} answers")
                        }
                    }
                    (progress.weakConcepts.firstOrNull() ?: progress.weakSourceAreas.firstOrNull())?.let { Text("Review next: $it") }
                    (progress.strongestConcepts.firstOrNull() ?: progress.strongSourceAreas.firstOrNull())?.let { Text("Strongest concept: $it") }
                }
            }
        }
        Text("Missing introductory text or a short section? Check for omitted text ranges. Existing chapters and quizzes will not change.")
        TextButton(onClick = onRepair, enabled = !state.loading) { Text("Check for omitted text") }
        state.documentRepairNotice?.let { Text(it, Modifier.semantics { liveRegion = LiveRegionMode.Polite }) }
        Row { TextButton(onClick = onAll, enabled = !state.loading) { Text("Entire document") }; TextButton(onClick = onClear, enabled = !state.loading) { Text("Clear selection") } }
        Text("${state.selectedChapterIds.size} of ${document.chapters.size} chapters selected",
            Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        if (state.documentExcerpts.isNotEmpty()) {
            Text("Excerpt mode: ${state.documentExcerpts.size} selected text ranges only", fontWeight = FontWeight.Bold)
            state.documentExcerpts.forEach { excerpt ->
                Text("${document.chapters.firstOrNull { it.id == excerpt.chapterId }?.title ?: excerpt.chapterId}: characters ${excerpt.start}–${excerpt.end}")
            }
            Text("Preview another chapter to add text. Any chapter checkbox, Entire document or Clear selection resets excerpt mode.")
        } else Text("Whole selected chapters. To choose an excerpt, open Preview and highlight source text.")
        document.chapters.forEach { chapter ->
            val selected = chapter.id in state.selectedChapterIds
            Row(Modifier.fillMaxWidth().toggleable(value = selected, enabled = !state.loading,
                role = androidx.compose.ui.semantics.Role.Checkbox, onValueChange = { onSelect(chapter.id) }).padding(12.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = selected, onCheckedChange = null, enabled = !state.loading)
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(chapter.title)
                    if (chapter.confidence < 0.6f) Text("Low-confidence text range: review before selecting", style = MaterialTheme.typography.bodySmall)
                }
            }
            TextButton(onClick = { onPreview(chapter.id) }, enabled = !state.loading) { Text("Preview: ${chapter.title}") }
        }
        Text("Large selections may need to be split into smaller quizzes. Questions use only the selected chapters.")
        val count = validDocumentQuestionCount(state.documentQuestionCountInput)
        Text("Number of questions")
        Row { listOf(5, 10, 15, 20).forEach { preset -> TextButton(onClick = { onCount(preset.toString()) }, enabled = !state.loading) { Text(preset.toString()) } } }
        OutlinedTextField(value = state.documentQuestionCountInput, onValueChange = onCount,
            label = { Text("Custom count (5–20)") }, singleLine = true, enabled = !state.loading,
            isError = count == null, modifier = Modifier.fillMaxWidth(),
            supportingText = { Text(if (count == null) "Enter a whole number from 5 to 20." else "Default: 10. Saved for this account on this device.") })
        Text("Difficulty")
        documentDifficulties.forEach { (value, label) ->
            Row(Modifier.fillMaxWidth().selectable(selected = state.documentDifficulty == value,
                enabled = !state.loading, role = androidx.compose.ui.semantics.Role.RadioButton,
                onClick = { onDifficulty(value) }).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = state.documentDifficulty == value, onClick = null, enabled = !state.loading)
                Text(label, modifier = Modifier.weight(1f))
            }
        }
        Text("Difficulty is a request, not a measured skill level. Offline generation supports Easy recall only; other levels require live generation.")
        Text("Question format")
        documentQuestionTypes.forEach { (value, label) ->
            Row(Modifier.fillMaxWidth().selectable(selected = state.documentQuestionType == value,
                enabled = !state.loading, role = androidx.compose.ui.semantics.Role.RadioButton,
                onClick = { onType(value) }).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = state.documentQuestionType == value, onClick = null, enabled = !state.loading)
                Text(label)
            }
        }
        Text("Choose one format per quiz. True / False and Yes / No require live generation.")
        DocumentSourceSearchControls(state, onQuery, onSearch, onUseResult)
        DocumentPdfPageControls(state, onLoadPages, onPageInput, onReviewPages, onConfirmPages)
        PrimaryButton(if (count == null) "Generate quiz" else "Generate $count questions", state.selectedChapterIds.isNotEmpty() && count != null && !state.loading, onCreate)
    }
}

@Composable
private fun DocumentPdfPageControls(state: AppUiState, onLoad: () -> Unit, onInput: (Boolean, String) -> Unit,
                                    onReview: () -> Unit, onConfirm: () -> Unit) {
    val document = state.document ?: return
    if (!document.name.endsWith(".pdf", ignoreCase = true)) return
    Text("Original PDF pages", style = MaterialTheme.typography.titleLarge)
    Text("Physical pages start at 1. These are not printed page labels or text-preview chunks. A confirmed range replaces all current chapter and excerpt selections.")
    TextButton(onClick = onLoad, enabled = !state.loading) { Text("Load original PDF page index") }
    val draft = state.pdfPageDraft?.takeIf { it.catalog.documentId == document.id } ?: return
    Text("${draft.catalog.pages.size} physical pages. Blank or scanned pages without extracted text cannot provide quiz content; OCR is not available.")
    OutlinedTextField(value = draft.first, onValueChange = { onInput(true, it) }, label = { Text("First physical PDF page") },
        singleLine = true, enabled = !state.loading, modifier = Modifier.fillMaxWidth())
    OutlinedTextField(value = draft.last, onValueChange = { onInput(false, it) }, label = { Text("Last physical PDF page (inclusive)") },
        singleLine = true, enabled = !state.loading, modifier = Modifier.fillMaxWidth())
    val range = validPdfPageRange(draft.first, draft.last, draft.catalog.pages.size)
    if (range == null) Text("Enter whole page numbers from 1 to ${draft.catalog.pages.size}, first no greater than last.")
    TextButton(onClick = onReview, enabled = !state.loading && range != null) { Text("Review original page range") }
    draft.reviewed?.let { scope ->
        Text("Review pages ${scope.first} to ${scope.last}. Your current selection has not changed.")
        scope.excerpts.forEach { excerpt ->
            Text("${document.chapters.firstOrNull { it.id == excerpt.chapterId }?.title ?: excerpt.chapterId}: source characters ${excerpt.start}–${excerpt.end}")
        }
        if (scope.emptyPages.isNotEmpty()) Text("No extracted text on pages: ${scope.emptyPages.joinToString()}")
        TextButton(onClick = onConfirm, enabled = !state.loading) { Text("Use these PDF pages instead of current selection") }
    }
}

@Composable
private fun DocumentSourceSearchControls(state: AppUiState, onQuery: (String) -> Unit, onSearch: () -> Unit, onUseResult: (Int) -> Unit) {
    Text("Find a topic or phrase", style = MaterialTheme.typography.titleLarge)
    Text("Search the checked chapters for an exact phrase first. If there is no phrase match, every important query word must occur in one bounded source passage. This does not infer synonyms or change your selection automatically. Search covers whole checked chapters, even in excerpt mode.")
    OutlinedTextField(value = state.sourceQuery, onValueChange = onQuery, label = { Text("Topic or source phrase (2–120 characters)") },
        singleLine = true, enabled = !state.loading, modifier = Modifier.fillMaxWidth())
    TextButton(onClick = onSearch, enabled = !state.loading && state.selectedChapterIds.isNotEmpty() && validSourceQuery(state.sourceQuery)) { Text("Search selected chapters") }
    state.documentSearch?.let { result ->
        Text(documentSearchStatus(result), Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        if (result.hasMore) Text("More passages match. Refine your topic or select fewer chapters.")
        result.hits.forEachIndexed { index, hit ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Result ${index + 1}: ${hit.title}", fontWeight = FontWeight.Bold)
                    Text("Source characters ${hit.start}–${hit.end}", style = MaterialTheme.typography.bodySmall)
                    Text(hit.text)
                    if (hit.truncated) Text("Context is cut at a source boundary limit. Review whether this passage has enough information.")
                    Text(if (state.documentExcerpts.isEmpty()) "Using this passage replaces whole-chapter selection." else "Using this passage adds an excerpt; overlapping selections are rejected.")
                    TextButton(onClick = { onUseResult(index) }, enabled = !state.loading) { Text("Use passage ${index + 1} as excerpt") }
                }
            }
        }
    }
}

@Composable
private fun DocumentPreviewScreen(state: AppUiState, onBack: () -> Unit, onPage: (Int) -> Unit, onExcerpt: (Int, Int) -> Unit) {
    val preview = state.documentPreview ?: return
    var selection by remember(preview) { mutableStateOf(androidx.compose.ui.text.input.TextFieldValue(preview.text)) }
    Page {
        TextButton(onClick = onBack, enabled = !state.loading) { Text("‹ Back to chapter selection") }
        Header("Source preview", preview.title, "Extracted text, not AI-generated. Preview chunks are not original PDF pages.")
        Text("Part ${preview.page + 1} of ${preview.totalPages} · Characters ${preview.start}–${preview.end}")
        Row {
            TextButton(onClick = { onPage(preview.page - 1) }, enabled = !state.loading && preview.page > 0) { Text("Previous part") }
            TextButton(onClick = { onPage(preview.page + 1) }, enabled = !state.loading && preview.page + 1 < preview.totalPages) { Text("Next part") }
        }
        OutlinedTextField(value = selection, onValueChange = { if (it.text == preview.text) selection = it },
            readOnly = true, enabled = !state.loading, modifier = Modifier.fillMaxWidth(),
            label = { Text("Source text — long press to highlight") })
        Text("Previewing alone does not change your quiz selection. Highlight text, then confirm below. Excerpts must contain enough material for your question count.")
        val selectedExcerpt = runCatching { excerptFromSelection(preview, selection.selection.start, selection.selection.end) }.getOrNull()
        selectedExcerpt?.let { Text("Selected source characters ${it.start}–${it.end}") }
        PrimaryButton(if (state.documentExcerpts.isEmpty()) "Use highlighted excerpt instead of whole chapters" else "Add highlighted excerpt", selectedExcerpt != null && !state.loading) {
            onExcerpt(selection.selection.start, selection.selection.end)
        }
    }
}

@Composable
private fun DocumentQuestionScreen(state: AppUiState, onAnswer: (String) -> Unit) {
    val question = state.question ?: return; var selected by remember(question.id) { mutableStateOf<String?>(null) }
    Page { Text("QUESTION ${question.ordinal} OF ${state.documentQuestionTotal}", color = Indigo, fontWeight = FontWeight.Bold); Text(requestedDifficultyLabel(state.savedQuizDifficulty), style = MaterialTheme.typography.bodySmall); Text(documentQuestionTypeLabel(state.savedQuizQuestionType), style = MaterialTheme.typography.bodySmall); Text(question.prompt, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface); question.options.forEach { AnswerChoice(it, selected == it) { selected = it } }; Text("Source: ${question.sourceReference}", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall); PrimaryButton("Check answer", selected != null && !state.loading) { selected?.let(onAnswer) } }
}

@Composable
private fun DocumentFeedbackScreen(state: AppUiState, onViewSource: (String) -> Unit, onContinue: () -> Unit) {
    val feedback = state.feedback ?: return; val color = if (feedback.correct) Success else Warning
    Page { Icon(if (feedback.correct) Icons.Outlined.CheckCircle else Icons.Outlined.ErrorOutline, null, tint = color, modifier = Modifier.size(48.dp)); Header("Study feedback", if (feedback.correct) "Correct!" else "Not quite", if (feedback.correct) "Nice work — keep building your streak." else "Your answer: ${feedback.selected}\nCorrect answer: ${feedback.answer}"); Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) { Text("Why", fontWeight = FontWeight.Bold); Text(feedback.explanation) } }; TextButton(onClick = { onViewSource(feedback.questionId) }, enabled = !state.loading) { Text("View source: ${feedback.source}") }; PrimaryButton(if (feedback.next == null) "See results" else "Next question", onClick = onContinue) }
}

@Composable
private fun DocumentResultsScreen(results: Results?, onViewSource: (String) -> Unit, onRetryMistakes: () -> Unit, onConfigureAgain: () -> Unit, onIncreaseDifficulty: () -> Unit, onAnotherDocument: () -> Unit, onBack: () -> Unit, difficulty: String?, questionType: String?, loading: Boolean) {
    results ?: return
    Page { Text(requestedDifficultyLabel(difficulty), style = MaterialTheme.typography.bodySmall); Text(documentQuestionTypeLabel(questionType), style = MaterialTheme.typography.bodySmall); Header("Session complete", "${results.correct} / ${results.total} correct", "Accuracy: ${(results.accuracy * 100).toInt()}%. Review missed concepts before moving on."); results.mistakes.forEach { mistake -> TipCard("Review question ${mistake.question.ordinal}", "${mistake.question.prompt}\nYour answer: ${mistake.selectedOption}\nCorrect answer: ${mistake.correctOption}\nWhy: ${mistake.explanation}\nSource: ${mistake.question.sourceReference}"); TextButton(onClick = { onViewSource(mistake.question.id) }, enabled = !loading) { Text("View source: ${mistake.question.sourceReference}") } }; if (results.mistakes.isNotEmpty()) PrimaryButton("Retry ${results.mistakes.size} incorrect ${if (results.mistakes.size == 1) "question" else "questions"}", enabled = !loading, onClick = onRetryMistakes); PrimaryButton("Configure another quiz", enabled = !loading, onClick = onConfigureAgain); nextDocumentDifficulty(difficulty)?.let { next -> PrimaryButton("Increase to ${next.replaceFirstChar(Char::uppercase)}", enabled = !loading, onClick = onIncreaseDifficulty) }; TextButton(onClick = onAnotherDocument, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Study another document") }; TextButton(onClick = onBack, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Return to learning path") } }
}

@Composable
private fun SourceEvidenceDialog(evidence: QuestionSourceEvidence, onClose: () -> Unit) {
    AlertDialog(onDismissRequest = onClose, title = { Text("Source passage") }, text = {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.verticalScroll(rememberScrollState())) {
            Text(evidence.reference, style = MaterialTheme.typography.bodySmall)
            Text(evidence.text)
            Text("Exact extracted source characters ${evidence.start}–${evidence.end}. This is not AI-generated.", style = MaterialTheme.typography.bodySmall)
            evidence.originalPdfPages.forEach { page ->
                val bitmap = remember(page.imageBase64) {
                    Base64.getDecoder().decode(page.imageBase64).let { bytes ->
                        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    }
                }
                bitmap?.let {
                    Text("Original PDF page ${page.page}", fontWeight = FontWeight.Bold)
                    Image(bitmap = it.asImageBitmap(), contentDescription = "Original PDF page ${page.page}",
                        contentScale = ContentScale.FillWidth, modifier = Modifier.fillMaxWidth())
                }
            }
        }
    }, confirmButton = { TextButton(onClick = onClose) { Text("Close") } })
}

@Composable
private fun LoadingOverlay(upload: DocumentUploadProgress? = null) = Box(
    Modifier.fillMaxSize().background(Color(0x990F172A)).padding(24.dp).semantics {
        paneTitle = "Loading learning content"
        liveRegion = LiveRegionMode.Polite
    }, contentAlignment = Alignment.Center) {
    Card(shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.padding(24.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            if (upload == null) {
                CircularProgressIndicator()
                Text("Preparing your learning session…")
            } else {
                Text(upload.title, style = MaterialTheme.typography.titleMedium)
                val fraction = upload.fraction
                if (fraction == null) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                else LinearProgressIndicator(progress = { fraction }, modifier = Modifier.fillMaxWidth())
                Text(upload.detail)
            }
        }
    }
}

@Composable
private fun ErrorDialog(message: String, onDismiss: () -> Unit) = AlertDialog(onDismissRequest = onDismiss, icon = { Icon(Icons.Outlined.ErrorOutline, null) }, title = { Text("We could not continue") }, text = { Text(message) }, confirmButton = { TextButton(onClick = onDismiss) { Text("Try again") } })
