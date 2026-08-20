package com.konetibalaji.learning

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.School
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { LearnlyApp() }
    }
}

private val StudyBlue = Color(0xFF2563EB)
private val SessionGreen = Color(0xFF047857)

@Composable
private fun LearnlyApp(viewModel: LearningViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    MaterialTheme(colorScheme = MaterialTheme.colorScheme.copy(primary = StudyBlue, secondary = SessionGreen)) {
        Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFFF8FAFC)) {
            Scaffold { padding ->
                Box(modifier = Modifier.fillMaxSize().padding(padding)) {
                    when (state.screen) {
                        Screen.SignIn -> SignInScreen(state.loading, viewModel::createAccount)
                        Screen.Home -> HomeScreen(state.loading, viewModel::upload)
                        Screen.Chapters -> ChaptersScreen(state, viewModel::selectChapter, viewModel::createQuiz)
                        Screen.Question -> QuestionScreen(state, viewModel::submitAnswer)
                        Screen.Feedback -> FeedbackScreen(state.feedback, viewModel::continueAfterFeedback)
                        Screen.Results -> ResultsScreen(state.results, viewModel::startAnotherDocument)
                    }
                    if (state.loading) LoadingOverlay()
                }
            }
        }
    }
    state.error?.let { message -> ErrorDialog(message, viewModel::clearError) }
}

@Composable
private fun AppHeader(overline: String, title: String, body: String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(overline.uppercase(), style = MaterialTheme.typography.labelLarge, color = StudyBlue, fontWeight = FontWeight.Bold)
        Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(body, style = MaterialTheme.typography.bodyLarge, color = Color(0xFF475569))
    }
}

@Composable
private fun SignInScreen(loading: Boolean, onCreateAccount: (String, String) -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 48.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        Icon(Icons.Outlined.School, contentDescription = null, tint = StudyBlue, modifier = Modifier.width(48.dp).height(48.dp))
        AppHeader("Learnly", "Study what matters.", "Turn your own study material into a focused learning session with instant explanations.")
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = email, onValueChange = { email = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Email address") }, singleLine = true)
        OutlinedTextField(value = password, onValueChange = { password = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Password") }, visualTransformation = PasswordVisualTransformation(), supportingText = { Text("Use at least 12 characters.") }, singleLine = true)
        Button(
            onClick = { onCreateAccount(email.trim(), password) }, enabled = !loading && email.isNotBlank() && password.length >= 12,
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) { Text("Create account and continue") }
        Text("Your documents stay tied to your account. Provider credentials never live in the app.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569))
    }
}

@Composable
private fun HomeScreen(loading: Boolean, onUpload: (android.content.Context, android.net.Uri) -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri -> uri?.let { onUpload(context, it) } }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 40.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp),
    ) {
        AppHeader("Your study space", "Start with one document.", "Choose a PDF, DOCX, or TXT file. We will find the sections before creating your quiz.")
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Icon(Icons.Outlined.Description, contentDescription = null, tint = StudyBlue)
                Text("Upload study material", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text("Up to 50 MB. Password-protected or scanned files are reported clearly before a study session begins.", color = Color(0xFF475569))
                Button(onClick = { picker.launch("application/*") }, enabled = !loading, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Choose document") }
            }
        }
        LearningPrinciple("One question at a time", "Answer, understand the explanation, then continue.")
        LearningPrinciple("Grounded in your material", "Every question includes the source section that supports it.")
    }
}

@Composable
private fun LearningPrinciple(title: String, body: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
        Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = SessionGreen)
        Column { Text(title, fontWeight = FontWeight.SemiBold); Text(body, color = Color(0xFF475569)) }
    }
}

@Composable
private fun ChaptersScreen(state: AppUiState, onSelect: (String) -> Unit, onCreateQuiz: () -> Unit) {
    val document = state.document ?: return
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 36.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        AppHeader("Review structure", "Choose what to study.", "We detected these sections in ${document.name}. You can generate a focused ten-question session from one section.")
        document.chapters.forEach { chapter ->
            val selected = chapter.id == state.selectedChapterId
            Card(
                colors = CardDefaults.cardColors(containerColor = if (selected) Color(0xFFEFF6FF) else Color.White),
                modifier = Modifier.fillMaxWidth().selectable(selected = selected, onClick = { onSelect(chapter.id) }, role = Role.RadioButton),
            ) {
                Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = selected, onClick = null)
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text(chapter.title, fontWeight = FontWeight.SemiBold)
                        Text(if (chapter.confidence >= .8f) "Detected with high confidence" else "Review this detected section", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569))
                    }
                }
            }
        }
        Button(onClick = onCreateQuiz, enabled = state.selectedChapterId != null && !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Generate 10 questions") }
    }
}

@Composable
private fun QuestionScreen(state: AppUiState, onAnswer: (String) -> Unit) {
    val question = state.question ?: return
    var selected by remember(question.id) { mutableStateOf<String?>(null) }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 36.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text("QUESTION ${question.ordinal} OF 10", color = StudyBlue, fontWeight = FontWeight.Bold)
        HorizontalDivider()
        Text(question.prompt, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
        question.options.forEach { option ->
            val chosen = selected == option
            Card(
                colors = CardDefaults.cardColors(containerColor = if (chosen) Color(0xFFEFF6FF) else Color.White),
                modifier = Modifier.fillMaxWidth().selectable(selected = chosen, onClick = { selected = option }, role = Role.RadioButton),
            ) {
                Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = chosen, onClick = null)
                    Spacer(Modifier.width(12.dp)); Text(option)
                }
            }
        }
        Text("Source: ${question.sourceReference}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569))
        Button(onClick = { selected?.let(onAnswer) }, enabled = selected != null && !state.loading, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Check answer") }
    }
}

@Composable
private fun FeedbackScreen(feedback: Feedback?, onContinue: () -> Unit) {
    feedback ?: return
    val color = if (feedback.correct) SessionGreen else Color(0xFFB45309)
    val title = if (feedback.correct) "Correct" else "Not quite"
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 40.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Icon(if (feedback.correct) Icons.Outlined.CheckCircle else Icons.Outlined.ErrorOutline, contentDescription = title, tint = color, modifier = Modifier.width(48.dp).height(48.dp))
        Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = color)
        if (!feedback.correct) {
            Text("Your answer", fontWeight = FontWeight.SemiBold); Text(feedback.selected)
            Text("Correct answer", fontWeight = FontWeight.SemiBold); Text(feedback.answer)
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color.White)) { Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { Text("Why", fontWeight = FontWeight.SemiBold); Text(feedback.explanation) } }
        Text("Source: ${feedback.source}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569))
        Button(onClick = onContinue, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text(if (feedback.next == null) "See results" else "Next question") }
    }
}

@Composable
private fun ResultsScreen(results: Results?, onStartAgain: () -> Unit) {
    results ?: return
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 40.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        AppHeader("Session complete", "${results.correct} / ${results.total} correct", "Accuracy: ${(results.accuracy * 100).toInt()}%. Review the concepts you missed before you move on.")
        if (results.mistakes.isEmpty()) Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFECFDF5))) { Text("Excellent work. You answered every completed question correctly.", modifier = Modifier.padding(20.dp), color = SessionGreen) }
        results.mistakes.forEach { mistake -> Card(colors = CardDefaults.cardColors(containerColor = Color.White)) { Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) { Text("Review question ${mistake.ordinal}", fontWeight = FontWeight.SemiBold); Text(mistake.prompt); Text("Source: ${mistake.sourceReference}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569)) } } }
        OutlinedButton(onClick = onStartAgain, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Study another document") }
    }
}

@Composable
private fun LoadingOverlay() {
    Box(modifier = Modifier.fillMaxSize().background(Color(0x990F172A)), contentAlignment = Alignment.Center) {
        Card { Row(modifier = Modifier.padding(24.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) { CircularProgressIndicator(); Text("Working with your study material…") } }
    }
}

@Composable
private fun ErrorDialog(message: String, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Outlined.ErrorOutline, contentDescription = null) },
        title = { Text("We could not continue") },
        text = { Text(message) },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Try again") } },
    )
}
