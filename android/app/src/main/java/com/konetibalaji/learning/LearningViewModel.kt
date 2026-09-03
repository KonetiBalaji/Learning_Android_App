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
    val chapterScores: Map<String, Int> = emptyMap(), val masteredChapterIds: Set<String> = emptySet(),
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
    LearningSubject("math", "Mathematics", "∑", 0, 0xFF4F46E5), LearningSubject("science", "Science", "⚗", 0, 0xFF2563EB),
    LearningSubject("english", "English", "Aa", 0, 0xFF10B981), LearningSubject("social", "Social Studies", "◎", 0, 0xFFF59E0B),
)
val mathChapters = listOf(
    MasteryChapter("fractions", "Fractions", 0), MasteryChapter("decimals", "Decimals", 0), MasteryChapter("percentages", "Percentages", 0),
    MasteryChapter("algebra", "Algebra", 0), MasteryChapter("geometry", "Geometry", 0, locked = true),
)
val chaptersBySubject = mapOf(
    "math" to mathChapters,
    "science" to listOf(
        MasteryChapter("cells", "Cells and Living Things", 0), MasteryChapter("matter", "Matter and Materials", 0),
        MasteryChapter("force-and-motion", "Force and Motion", 0), MasteryChapter("ecosystems", "Ecosystems", 0, locked = true),
    ),
    "english" to listOf(
        MasteryChapter("grammar", "Grammar", 0), MasteryChapter("reading-comprehension", "Reading Comprehension", 0),
        MasteryChapter("vocabulary", "Vocabulary", 0), MasteryChapter("writing", "Writing", 0, locked = true),
    ),
    "social" to listOf(
        MasteryChapter("geography", "Geography", 0), MasteryChapter("history", "History", 0),
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
    val canResumeMastery: Boolean = false,
    val assessmentPoints: Int? = null, val assessmentFeedback: String? = null,
)

class LearningViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences("learn-smart", Context.MODE_PRIVATE)
    private val tokenStore = SessionTokenStore(preferences)
    private val api = LearningApi(null, tokenStore::write)
    private val savedGrade = preferences.getInt("grade", 0).takeIf { it in 1..12 }
    private val mutableState = MutableStateFlow(AppUiState(
        screen = Screen.SignIn, loading = true,
        grade = savedGrade, darkMode = preferences.getBoolean("dark_mode", false),
        accountEmail = preferences.getString("email", "").orEmpty(),
        canResumeMastery = preferences.contains("active_mastery:${preferences.getString("email", "").orEmpty().lowercase()}"),
    ))
    val state: StateFlow<AppUiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            val restored = withContext(Dispatchers.IO) { runCatching { tokenStore.read() } }
            api.restoreToken(restored.getOrNull())
            mutableState.value = mutableState.value.copy(loading = false,
                screen = if (api.hasToken) (if (savedGrade == null) Screen.Grade else Screen.Subjects) else Screen.SignIn,
                error = if (restored.isFailure) "Unable to restore the saved session. Please sign in." else null)
            if (api.hasToken && preferences.contains(activeSessionKey())) resumeLearning()
            else if (api.hasToken && savedGrade != null) refreshProgress()
        }
    }

    private suspend fun loadProgress() {
        val grade = mutableState.value.grade ?: return
        val snapshot = api.progressDashboard(grade)
        val unlocked = chaptersBySubject.flatMap { (subjectId, chapters) ->
            chapters.mapIndexedNotNull { index, chapter ->
                if (index > 0 && "$subjectId:${chapters[index - 1].id}" in snapshot.masteredChapterIds) "$subjectId:${chapter.id}" else null
            }
        }.toSet()
        mutableState.value = mutableState.value.copy(progressSnapshot = snapshot, unlockedChapterIds = unlocked)
    }

    fun refreshProgress() = perform(null) { loadProgress() }

    private fun activeSessionKey() = "active_mastery:${mutableState.value.accountEmail.lowercase()}"

    fun resumeLearning() {
        val sessionId = preferences.getString(activeSessionKey(), null) ?: return
        perform(null) {
            val resumed = api.resumeMastery(sessionId)
            val subject = learningSubjects.firstOrNull { it.id == resumed.subjectId }
                ?: error("The saved subject is not available in this version.")
            val chapter = chaptersBySubject[subject.id]?.firstOrNull { it.id == resumed.chapterId }
                ?: error("The saved chapter is not available in this version.")
            mutableState.value = mutableState.value.copy(
                grade = resumed.grade, subject = subject, masteryChapter = chapter,
                masterySessionId = sessionId, adaptiveQuestion = resumed.question,
                adaptiveOrdinal = resumed.ordinal, adaptiveTotal = resumed.total,
                tutorLesson = resumed.tutor, selectedDiagnosticAnswer = resumed.selected,
                masteryScore = resumed.score, coachingRound = resumed.coachingRounds,
                assessmentPoints = resumed.assessmentPoints, assessmentFeedback = resumed.assessmentFeedback,
                screen = screenForMasteryStatus(resumed.status),
            )
        }
    }

    fun authenticate(email: String, password: String, createAccount: Boolean) = perform(Screen.Grade) {
        if (createAccount) api.register(email, password) else api.login(email, password)
        preferences.edit().putString("email", email).remove("grade").remove("unlocked").apply()
        mutableState.value = AppUiState(accountEmail = email, darkMode = mutableState.value.darkMode,
            canResumeMastery = preferences.contains("active_mastery:${email.lowercase()}"))
    }
    fun selectGrade(grade: Int) { preferences.edit().putInt("grade", grade).apply(); mutableState.value = mutableState.value.copy(grade = grade, screen = Screen.Subjects, progressSnapshot = null, unlockedChapterIds = emptySet()); refreshProgress() }
    fun selectSubject(subject: LearningSubject) { mutableState.value = mutableState.value.copy(subject = subject, screen = Screen.MasteryChapters) }
    fun selectMasteryChapter(chapter: MasteryChapter) {
        val current = mutableState.value
        val chapterKey = "${current.subject?.id}:${chapter.id}"
        if (chapter.locked && chapterKey !in current.unlockedChapterIds) return
        perform(null) {
            val started = api.startDiagnostic(current.grade ?: 6, requireNotNull(current.subject).id, chapter.id)
            preferences.edit().putString(activeSessionKey(), started.id).apply()
            mutableState.value = current.copy(
                masteryChapter = chapter, diagnosticIndex = 0, diagnosticCorrect = 0, coachingRound = 0,
                masterySessionId = started.id, adaptiveQuestion = started.question, adaptiveOrdinal = started.ordinal,
                adaptiveTotal = started.total, selectedDiagnosticAnswer = null, screen = Screen.Diagnostic,
                canResumeMastery = true,
                assessmentPoints = null, assessmentFeedback = null,
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
                screen = screenForLearningAction(outcome.nextAction),
                practiceResult = null, showHint = false,
                assessmentPoints = null, assessmentFeedback = null,
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
                screen = screenForLearningAction(outcome.nextAction),
                adaptiveQuestion = outcome.nextQuestion ?: current.adaptiveQuestion,
                adaptiveOrdinal = outcome.ordinal ?: current.adaptiveOrdinal,
                selectedDiagnosticAnswer = null, practiceResult = null, rewrite = "",
                coachingRound = current.coachingRound + if (outcome.nextAction == "tutor") 1 else 0,
                masteryScore = outcome.score,
                masteryConfidence = outcome.confidence,
                assessmentPoints = outcome.assessmentPoints, assessmentFeedback = outcome.assessmentFeedback,
                tutorLesson = if (outcome.coaching == null) current.tutorLesson else current.tutorLesson?.copy(explanation = outcome.coaching),
            )
        }
    }
    fun continueFromMastery() {
        preferences.edit().remove(activeSessionKey()).apply()
        mutableState.value = mutableState.value.copy(canResumeMastery = false)
        perform(Screen.MasteryChapters) { loadProgress() }
    }
    fun openParentDashboard() {
        val current = mutableState.value
        perform(null) { mutableState.value = current.copy(progressSnapshot = api.progressWithWeekly(current.grade ?: 8), screen = Screen.ParentDashboard) }
    }
    fun openSettings() { mutableState.value = mutableState.value.copy(screen = Screen.Settings) }
    fun setDarkMode(enabled: Boolean) { preferences.edit().putBoolean("dark_mode", enabled).apply(); mutableState.value = mutableState.value.copy(darkMode = enabled) }
    fun signOut() = perform(Screen.SignIn) { tokenStore.clear(); api.signOut(); preferences.edit().remove("email").remove("grade").remove("unlocked").apply(); mutableState.value = AppUiState(darkMode = mutableState.value.darkMode) }
    fun deleteAccount() = perform(null) { api.deleteAccount(); tokenStore.clear(); preferences.edit().clear().apply(); mutableState.value = AppUiState() }
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
    fun restoreToken(value: String?) { token = value }
    private fun acceptToken(response: JSONObject) { val accepted = response.getString("access_token"); saveToken(accepted); token = accepted }
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
    data class RewriteResult(val mastered: Boolean, val score: Int, val confidence: String, val coaching: String?, val nextAction: String, val nextQuestion: DiagnosticQuestion?, val ordinal: Int?, val assessmentPoints: Int?, val assessmentFeedback: String?)
    data class ResumedMastery(val grade: Int, val subjectId: String, val chapterId: String, val status: String, val question: DiagnosticQuestion?, val ordinal: Int, val total: Int, val tutor: TutorLesson?, val selected: String?, val score: Int, val coachingRounds: Int, val assessmentPoints: Int?, val assessmentFeedback: String?)
    fun resumeMastery(sessionId: String): ResumedMastery {
        val response = request("GET", "/v1/mastery/sessions/$sessionId", null)
        val question = response.optJSONObject("question")
        val tutor = response.optJSONObject("tutor")?.let { TutorLesson(it.getString("title"), it.getString("explanation"), it.getString("worked_example"), it.getString("hint"), it.getString("practice_prompt")) }
        return ResumedMastery(response.getInt("grade"), response.getString("subject_id"), response.getString("chapter_id"), response.getString("status"), question?.let(::adaptiveQuestion), question?.getInt("ordinal") ?: 1, question?.getInt("total") ?: 3, tutor, if (response.isNull("selected_option")) null else response.getString("selected_option"), (response.getDouble("mastery_score") * 100).toInt(), response.getInt("coaching_rounds"), if (response.isNull("assessment_points")) null else response.getInt("assessment_points"), if (response.isNull("assessment_feedback")) null else response.getString("assessment_feedback"))
    }
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
    fun submitRewrite(sessionId: String, rewrite: String): RewriteResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/rewrite", JSONObject().put("response", rewrite).toString())
        val next = response.optJSONObject("next_question")
        return RewriteResult(response.getBoolean("mastery_achieved"), (response.getDouble("mastery_score") * 100).toInt(),
            response.getString("confidence").replace('_', ' ').replaceFirstChar(Char::uppercase),
            if (response.isNull("coaching")) null else response.getString("coaching"), response.getString("next_action"),
            next?.let(::adaptiveQuestion), next?.getInt("ordinal"),
            if (response.isNull("assessment_points")) null else response.getInt("assessment_points"),
            if (response.isNull("assessment_feedback")) null else response.getString("assessment_feedback"))
    }
    fun progressDashboard(grade: Int): ProgressSnapshot {
        val response = request("GET", "/v1/progress/dashboard?grade=$grade", null)
        val subjectsObject = response.getJSONObject("subjects")
        val subjects = subjectsObject.keys().asSequence().associateWith { (subjectsObject.getDouble(it) * 100).toInt() }
        val chapters = response.getJSONArray("chapters")
        val scores = (0 until chapters.length()).associate { index -> val item = chapters.getJSONObject(index); "${item.getString("subject_id")}:${item.getString("chapter_id")}" to (item.getDouble("mastery") * 100).toInt() }
        val mastered = (0 until chapters.length()).mapNotNull { index -> val item = chapters.getJSONObject(index); if (item.getString("status") == "mastered" && item.getDouble("mastery") >= 1.0) "${item.getString("subject_id")}:${item.getString("chapter_id")}" else null }.toSet()
        return ProgressSnapshot(subjects, response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings(), chapterScores = scores, masteredChapterIds = mastered)
    }
    fun weeklyReport(grade: Int): ProgressSnapshot { val response = request("GET", "/v1/progress/weekly-report?grade=$grade", null); return ProgressSnapshot(emptyMap(), response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings(), response.getInt("questions_answered"), (response.getDouble("accuracy") * 100).toInt(), response.getInt("mastered_chapters"), response.getDouble("estimated_exam_readiness").toInt(), response.getString("readiness_label").replace('_', ' ').replaceFirstChar(Char::uppercase)) }
    fun progressWithWeekly(grade: Int): ProgressSnapshot { val dashboard = progressDashboard(grade); val weekly = weeklyReport(grade); return dashboard.copy(questionsAnswered = weekly.questionsAnswered, accuracy = weekly.accuracy, masteredChapters = weekly.masteredChapters, examReadiness = weekly.examReadiness, readinessLabel = weekly.readinessLabel, weakAreas = weekly.weakAreas.ifEmpty { dashboard.weakAreas }, recommendations = weekly.recommendations.ifEmpty { dashboard.recommendations }) }
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
