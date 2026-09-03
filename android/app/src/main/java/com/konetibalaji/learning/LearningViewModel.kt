package com.konetibalaji.learning

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

data class Chapter(val id: String, val title: String, val confidence: Float)
data class StudyDocument(val id: String, val name: String, val chapters: List<Chapter>)
data class QuizQuestion(val id: String, val ordinal: Int, val prompt: String, val options: List<String>, val sourceReference: String)
data class Feedback(val correct: Boolean, val selected: String, val answer: String, val explanation: String, val source: String, val next: QuizQuestion?)
data class Results(val answered: Int, val total: Int, val correct: Int, val accuracy: Float, val mistakes: List<QuizQuestion>)

data class LearningSubject(val id: String, val title: String, val icon: String, val progress: Int, val accent: Long)
data class MasteryChapter(val id: String, val title: String, val progress: Int, val locked: Boolean = false)
data class DiagnosticQuestion(val prompt: String, val options: List<String>, val correct: String)
data class TutorLesson(val title: String, val explanation: String, val workedExample: String, val hint: String, val practicePrompt: String)
data class ProgressSnapshot(
    val subjects: Map<String, Int>, val weakAreas: List<String>, val recommendations: List<String>,
    val questionsAnswered: Int = 0, val accuracy: Int = 0, val masteredChapters: Int = 0,
    val examReadiness: Int = 0, val readinessLabel: String = "Needs support",
)

sealed interface Screen {
    data object SignIn : Screen; data object Grade : Screen; data object Subjects : Screen; data object MasteryChapters : Screen
    data object Diagnostic : Screen; data object Tutor : Screen; data object Practice : Screen; data object Rewrite : Screen
    data object Mastery : Screen; data object ParentDashboard : Screen; data object Home : Screen; data object Chapters : Screen
    data object Question : Screen; data object Feedback : Screen; data object Results : Screen; data object Settings : Screen
}

val fractionQuestions = listOf(
    DiagnosticQuestion("What is 3/4 + 1/4?", listOf("1/2", "1", "3/8", "2"), "1"),
    DiagnosticQuestion("Which fraction is equal to 1/2?", listOf("2/6", "3/6", "4/6", "5/6"), "3/6"),
    DiagnosticQuestion("What is 5/8 - 1/8?", listOf("4/8", "4/16", "5/7", "6/8"), "4/8"),
)

val learningSubjects = listOf(
    LearningSubject("math", "Mathematics", "∑", 72, 0xFF4F46E5), LearningSubject("science", "Science", "⚗", 65, 0xFF2563EB),
    LearningSubject("english", "English", "Aa", 82, 0xFF10B981), LearningSubject("social", "Social Studies", "◎", 48, 0xFFF59E0B),
)
val mathChapters = listOf(
    MasteryChapter("fractions", "Fractions", 80), MasteryChapter("decimals", "Decimals", 60), MasteryChapter("percentages", "Percentages", 20),
    MasteryChapter("algebra", "Algebra", 0), MasteryChapter("geometry", "Geometry", 0, locked = true),
)
val chaptersBySubject = mapOf(
    "math" to mathChapters,
    "science" to listOf(
        MasteryChapter("cells", "Cells and Living Things", 35), MasteryChapter("matter", "Matter and Materials", 10),
        MasteryChapter("force-and-motion", "Force and Motion", 0), MasteryChapter("ecosystems", "Ecosystems", 0, locked = true),
    ),
    "english" to listOf(
        MasteryChapter("grammar", "Grammar", 55), MasteryChapter("reading-comprehension", "Reading Comprehension", 30),
        MasteryChapter("vocabulary", "Vocabulary", 15), MasteryChapter("writing", "Writing", 0, locked = true),
    ),
    "social" to listOf(
        MasteryChapter("geography", "Geography", 40), MasteryChapter("history", "History", 20),
        MasteryChapter("civics", "Civics", 0), MasteryChapter("economics", "Economics", 0, locked = true),
    ),
)

data class AppUiState(
    val screen: Screen = Screen.SignIn, val loading: Boolean = false, val error: String? = null, val grade: Int? = null,
    val subject: LearningSubject? = null, val masteryChapter: MasteryChapter? = null, val diagnosticIndex: Int = 0, val diagnosticCorrect: Int = 0,
    val selectedDiagnosticAnswer: String? = null, val practiceResult: Boolean? = null, val showHint: Boolean = false, val coachingRound: Int = 0, val rewrite: String = "",
    val masterySessionId: String? = null, val adaptiveQuestion: DiagnosticQuestion? = null, val adaptiveOrdinal: Int = 1,
    val adaptiveTotal: Int = fractionQuestions.size, val tutorLesson: TutorLesson? = null, val masteryScore: Int = 0,
    val masteryConfidence: String = "Developing", val progressSnapshot: ProgressSnapshot? = null,
    val unlockedChapterIds: Set<String> = emptySet(), val darkMode: Boolean = false, val accountEmail: String = "",
    val document: StudyDocument? = null, val selectedChapterId: String? = null, val quizId: String? = null, val question: QuizQuestion? = null,
    val feedback: Feedback? = null, val results: Results? = null,
)

class LearningViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences("learn-smart", Context.MODE_PRIVATE)
    private val api = LearningApi(preferences.getString("token", null)) { token -> preferences.edit().putString("token", token).apply() }
    private val savedGrade = preferences.getInt("grade", 0).takeIf { it in 1..12 }
    private val mutableState = MutableStateFlow(AppUiState(
        screen = if (api.hasToken) (if (savedGrade == null) Screen.Grade else Screen.Subjects) else Screen.SignIn,
        grade = savedGrade, darkMode = preferences.getBoolean("dark_mode", false),
        unlockedChapterIds = preferences.getStringSet("unlocked", emptySet()).orEmpty(),
        accountEmail = preferences.getString("email", "").orEmpty(),
    ))
    val state: StateFlow<AppUiState> = mutableState.asStateFlow()

    fun authenticate(email: String, password: String, createAccount: Boolean) = perform(if (savedGrade == null) Screen.Grade else Screen.Subjects) {
        if (createAccount) api.register(email, password) else api.login(email, password)
        preferences.edit().putString("email", email).apply()
        mutableState.value = mutableState.value.copy(accountEmail = email)
    }
    fun selectGrade(grade: Int) { preferences.edit().putInt("grade", grade).apply(); mutableState.value = mutableState.value.copy(grade = grade, screen = Screen.Subjects) }
    fun selectSubject(subject: LearningSubject) { mutableState.value = mutableState.value.copy(subject = subject, screen = Screen.MasteryChapters) }
    fun selectMasteryChapter(chapter: MasteryChapter) {
        val current = mutableState.value
        val chapterKey = "${current.subject?.id}:${chapter.id}"
        if (chapter.locked && chapterKey !in current.unlockedChapterIds) return
        perform(null) {
            val started = api.startDiagnostic(current.grade ?: 6, requireNotNull(current.subject).id, chapter.id)
            mutableState.value = current.copy(
                masteryChapter = chapter, diagnosticIndex = 0, diagnosticCorrect = 0, coachingRound = 0,
                masterySessionId = started.id, adaptiveQuestion = started.question, adaptiveOrdinal = started.ordinal,
                adaptiveTotal = started.total, selectedDiagnosticAnswer = null, screen = Screen.Diagnostic,
            )
        }
    }
    fun selectDiagnosticAnswer(answer: String) { mutableState.value = mutableState.value.copy(selectedDiagnosticAnswer = answer) }

    fun submitDiagnostic() {
        val current = mutableState.value; val selected = current.selectedDiagnosticAnswer ?: return
        perform(null) {
            val outcome = api.answerDiagnostic(requireNotNull(current.masterySessionId), selected)
            mutableState.value = current.copy(
                diagnosticIndex = outcome.ordinal - 1,
                diagnosticCorrect = current.diagnosticCorrect + if (outcome.correct) 1 else 0,
                adaptiveQuestion = outcome.nextQuestion ?: current.adaptiveQuestion,
                adaptiveOrdinal = outcome.ordinal,
                selectedDiagnosticAnswer = if (outcome.correct) null else selected,
                tutorLesson = outcome.tutor,
                masteryScore = outcome.masteryScore,
                screen = when (outcome.nextAction) { "mastery" -> Screen.Mastery; "tutor" -> Screen.Tutor; else -> Screen.Diagnostic },
                practiceResult = null, showHint = false,
            )
        }
    }

    fun startPractice() { mutableState.value = mutableState.value.copy(screen = Screen.Practice, practiceResult = null, showHint = false) }
    fun showHint() { mutableState.value = mutableState.value.copy(showHint = true) }
    fun checkPractice(answer: String) {
        val current = mutableState.value
        perform(null) {
            val outcome = api.submitPractice(requireNotNull(current.masterySessionId), answer)
            mutableState.value = current.copy(practiceResult = outcome.first, showHint = !outcome.first, error = null)
        }
    }
    fun moveToRewrite() { mutableState.value = mutableState.value.copy(screen = Screen.Rewrite, rewrite = "") }
    fun updateRewrite(value: String) { mutableState.value = mutableState.value.copy(rewrite = value) }
    fun submitRewrite() {
        val current = mutableState.value
        perform(null) {
            val outcome = api.submitRewrite(requireNotNull(current.masterySessionId), current.rewrite)
            mutableState.value = current.copy(
                screen = if (outcome.mastered) Screen.Mastery else Screen.Tutor,
                coachingRound = current.coachingRound + if (outcome.mastered) 0 else 1,
                masteryScore = outcome.score,
                masteryConfidence = outcome.confidence,
                tutorLesson = if (outcome.coaching == null) current.tutorLesson else current.tutorLesson?.copy(explanation = outcome.coaching),
            )
        }
    }
    fun continueFromMastery() {
        val current = mutableState.value
        val subjectId = current.subject?.id
        val chapters = chaptersBySubject[subjectId].orEmpty()
        val currentIndex = chapters.indexOfFirst { it.id == current.masteryChapter?.id }
        val next = chapters.getOrNull(currentIndex + 1)
        val unlocked = if (subjectId != null && next != null) current.unlockedChapterIds + "$subjectId:${next.id}" else current.unlockedChapterIds
        preferences.edit().putStringSet("unlocked", unlocked).apply()
        mutableState.value = current.copy(screen = Screen.MasteryChapters, unlockedChapterIds = unlocked)
    }
    fun openParentDashboard() {
        val current = mutableState.value
        perform(null) { mutableState.value = current.copy(progressSnapshot = api.progressWithWeekly(), screen = Screen.ParentDashboard) }
    }
    fun openSettings() { mutableState.value = mutableState.value.copy(screen = Screen.Settings) }
    fun setDarkMode(enabled: Boolean) { preferences.edit().putBoolean("dark_mode", enabled).apply(); mutableState.value = mutableState.value.copy(darkMode = enabled) }
    fun signOut() { api.signOut(); preferences.edit().remove("token").apply(); mutableState.value = AppUiState(darkMode = mutableState.value.darkMode) }
    fun deleteAccount() = perform(null) { api.deleteAccount(); preferences.edit().clear().apply(); mutableState.value = AppUiState() }
    fun changeGrade() { mutableState.value = mutableState.value.copy(screen = Screen.Grade) }
    fun backToSubjects() { mutableState.value = mutableState.value.copy(screen = Screen.Subjects) }
    fun startDocumentStudy() { mutableState.value = mutableState.value.copy(screen = Screen.Home) }

    fun upload(context: Context, uri: Uri) = perform(Screen.Chapters) { val document = api.upload(context.contentResolver, uri); mutableState.value = mutableState.value.copy(document = document, selectedChapterId = document.chapters.firstOrNull()?.id) }
    fun selectChapter(chapterId: String) { mutableState.value = mutableState.value.copy(selectedChapterId = chapterId) }
    fun createQuiz() = perform(Screen.Question) { val current = mutableState.value; val quiz = api.createQuiz(requireNotNull(current.document).id, requireNotNull(current.selectedChapterId)); mutableState.value = current.copy(quizId = quiz.first, question = quiz.second, feedback = null, results = null) }
    fun submitAnswer(option: String) = perform(Screen.Feedback) { val current = mutableState.value; mutableState.value = current.copy(feedback = api.answer(requireNotNull(current.quizId), requireNotNull(current.question).id, option)) }
    fun continueAfterFeedback() { val current = mutableState.value; val feedback = current.feedback ?: return; if (feedback.next != null) mutableState.value = current.copy(screen = Screen.Question, question = feedback.next, feedback = null) else loadResults() }
    fun loadResults() = perform(Screen.Results) { mutableState.value = mutableState.value.copy(results = api.results(requireNotNull(mutableState.value.quizId))) }
    fun startAnotherDocument() { mutableState.value = mutableState.value.copy(screen = Screen.Home, document = null, quizId = null, results = null) }
    fun clearError() { mutableState.value = mutableState.value.copy(error = null) }

    private fun perform(destination: Screen?, block: suspend () -> Unit) = viewModelScope.launch {
        mutableState.value = mutableState.value.copy(loading = true, error = null)
        runCatching { withContext(Dispatchers.IO) { block() } }.onSuccess { mutableState.value = mutableState.value.copy(screen = destination ?: mutableState.value.screen, loading = false) }.onFailure { mutableState.value = mutableState.value.copy(loading = false, error = it.message ?: "Something went wrong. Please try again.") }
    }
}

private class LearningApi(initialToken: String?, private val saveToken: (String) -> Unit) {
    private var token: String? = initialToken; private val baseUrl = BuildConfig.API_BASE_URL
    val hasToken: Boolean get() = token != null
    private fun acceptToken(response: JSONObject) { token = response.getString("access_token"); saveToken(requireNotNull(token)) }
    fun register(email: String, password: String) = acceptToken(request("POST", "/v1/auth/register", JSONObject().put("email", email).put("password", password).toString()))
    fun login(email: String, password: String) = acceptToken(request("POST", "/v1/auth/login", JSONObject().put("email", email).put("password", password).toString()))
    fun signOut() { token = null }
    fun deleteAccount() { requestNoContent("DELETE", "/v1/account"); token = null }
    fun upload(resolver: ContentResolver, uri: Uri): StudyDocument {
        val name = resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor -> cursor.moveToFirst(); cursor.getString(cursor.getColumnIndexOrThrow(android.provider.OpenableColumns.DISPLAY_NAME)) } ?: "study-material.txt"
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() } ?: error("The selected file could not be read"); val boundary = "Learnly-${UUID.randomUUID()}"; val connection = connection("POST", "/v1/documents", "multipart/form-data; boundary=$boundary")
        BufferedOutputStream(connection.outputStream).use { output -> output.write("--$boundary\r\n".toByteArray()); output.write("Content-Disposition: form-data; name=\"file\"; filename=\"${name.replace("\"", "")}\"\r\n".toByteArray()); output.write("Content-Type: ${resolver.getType(uri) ?: "application/octet-stream"}\r\n\r\n".toByteArray()); output.write(bytes); output.write("\r\n--$boundary--\r\n".toByteArray()) }
        return document(readJson(connection))
    }
    fun createQuiz(documentId: String, chapterId: String): Pair<String, QuizQuestion> { val response = request("POST", "/v1/documents/$documentId/quizzes", JSONObject().put("chapter_ids", JSONArray().put(chapterId)).put("question_count", 10).toString()); return response.getString("id") to question(response.getJSONObject("first_question")) }
    fun answer(quizId: String, questionId: String, option: String): Feedback { val response = request("POST", "/v1/quizzes/$quizId/questions/$questionId/answer", JSONObject().put("selected_option", option).toString()); return Feedback(response.getBoolean("correct"), response.getString("selected_option"), response.getString("correct_option"), response.getString("explanation"), response.getString("source_reference"), response.optJSONObject("next_question")?.let(::question)) }
    fun results(quizId: String): Results { val response = request("GET", "/v1/quizzes/$quizId/results", null); return Results(response.getInt("answered"), response.getInt("total"), response.getInt("correct"), response.getDouble("accuracy").toFloat(), response.getJSONArray("mistakes").toQuestionList()) }
    data class StartedDiagnostic(val id: String, val question: DiagnosticQuestion, val ordinal: Int, val total: Int)
    data class DiagnosticResult(val correct: Boolean, val nextAction: String, val nextQuestion: DiagnosticQuestion?, val ordinal: Int, val masteryScore: Int, val tutor: TutorLesson?)
    data class RewriteResult(val mastered: Boolean, val score: Int, val confidence: String, val coaching: String?)
    fun startDiagnostic(grade: Int, subjectId: String, chapterId: String): StartedDiagnostic {
        val response = request("POST", "/v1/mastery/diagnostics", JSONObject().put("grade", grade).put("subject_id", subjectId).put("chapter_id", chapterId).toString())
        val question = response.getJSONObject("question")
        return StartedDiagnostic(response.getString("id"), adaptiveQuestion(question), question.getInt("ordinal"), question.getInt("total"))
    }
    fun answerDiagnostic(sessionId: String, selected: String): DiagnosticResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/diagnostic-answer", JSONObject().put("selected_option", selected).toString())
        val next = response.optJSONObject("next_question")
        val tutor = response.optJSONObject("tutor")?.let { TutorLesson(it.getString("title"), it.getString("explanation"), it.getString("worked_example"), it.getString("hint"), it.getString("practice_prompt")) }
        return DiagnosticResult(response.getBoolean("correct"), response.getString("next_action"), next?.let(::adaptiveQuestion), next?.optInt("ordinal") ?: 1, (response.getDouble("mastery_score") * 100).toInt(), tutor)
    }
    fun submitPractice(sessionId: String, answer: String): Pair<Boolean, String?> { val response = request("POST", "/v1/mastery/sessions/$sessionId/practice", JSONObject().put("response", answer).toString()); return response.getBoolean("correct") to response.optString("hint").takeIf(String::isNotBlank) }
    fun submitRewrite(sessionId: String, rewrite: String): RewriteResult { val response = request("POST", "/v1/mastery/sessions/$sessionId/rewrite", JSONObject().put("response", rewrite).toString()); return RewriteResult(response.getBoolean("mastery_achieved"), (response.getDouble("mastery_score") * 100).toInt(), response.getString("confidence").replace('_', ' ').replaceFirstChar(Char::uppercase), response.optString("coaching").takeIf(String::isNotBlank)) }
    fun progressDashboard(): ProgressSnapshot { val response = request("GET", "/v1/progress/dashboard", null); val subjectsObject = response.getJSONObject("subjects"); val subjects = subjectsObject.keys().asSequence().associateWith { (subjectsObject.getDouble(it) * 100).toInt() }; return ProgressSnapshot(subjects, response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings()) }
    fun weeklyReport(): ProgressSnapshot { val response = request("GET", "/v1/progress/weekly-report", null); return ProgressSnapshot(emptyMap(), response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings(), response.getInt("questions_answered"), (response.getDouble("accuracy") * 100).toInt(), response.getInt("mastered_chapters"), response.getDouble("estimated_exam_readiness").toInt(), response.getString("readiness_label").replace('_', ' ').replaceFirstChar(Char::uppercase)) }
    fun progressWithWeekly(): ProgressSnapshot { val dashboard = progressDashboard(); val weekly = weeklyReport(); return dashboard.copy(questionsAnswered = weekly.questionsAnswered, accuracy = weekly.accuracy, masteredChapters = weekly.masteredChapters, examReadiness = weekly.examReadiness, readinessLabel = weekly.readinessLabel, weakAreas = weekly.weakAreas.ifEmpty { dashboard.weakAreas }, recommendations = weekly.recommendations.ifEmpty { dashboard.recommendations }) }
    private fun request(method: String, path: String, body: String?): JSONObject { val connection = connection(method, path, "application/json"); if (body != null) connection.outputStream.use { it.write(body.toByteArray()) }; return readJson(connection) }
    private fun requestNoContent(method: String, path: String) { val response = connection(method, path, "application/json"); val status = response.responseCode; if (status !in 200..299) throw IllegalStateException("Request failed ($status)") }
    private fun connection(method: String, path: String, contentType: String): HttpURLConnection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply { requestMethod = method; connectTimeout = 15_000; readTimeout = 30_000; doInput = true; setRequestProperty("Content-Type", contentType); token?.let { setRequestProperty("Authorization", "Bearer $it") }; if (method == "POST" || method == "PUT" || method == "PATCH") doOutput = true }
    private fun readJson(connection: HttpURLConnection): JSONObject { val status = connection.responseCode; val text = (if (status in 200..299) connection.inputStream else connection.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty(); if (status !in 200..299) throw IllegalStateException(JSONObject(text.ifBlank { "{}" }).optString("detail", "Request failed ($status)")); return JSONObject(text) }
    private fun document(value: JSONObject) = StudyDocument(value.getString("id"), value.getString("original_name"), value.getJSONArray("chapters").let { array -> (0 until array.length()).map { index -> array.getJSONObject(index).let { Chapter(it.getString("id"), it.getString("title"), it.getDouble("confidence").toFloat()) } } })
    private fun question(value: JSONObject) = QuizQuestion(value.getString("id"), value.getInt("ordinal"), value.getString("prompt"), value.getJSONArray("options").let { array -> (0 until array.length()).map(array::getString) }, value.getString("source_reference"))
    private fun adaptiveQuestion(value: JSONObject) = DiagnosticQuestion(value.getString("prompt"), value.getJSONArray("options").strings(), "")
    private fun JSONArray.toQuestionList(): List<QuizQuestion> = (0 until length()).map { question(getJSONObject(it)) }
    private fun JSONArray.strings(): List<String> = (0 until length()).map(::getString)
}
