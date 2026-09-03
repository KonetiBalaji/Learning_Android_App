package com.konetibalaji.learning

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedOutputStream
import java.io.IOException
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
    data object DocumentLibrary : Screen
    data object Interests : Screen
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
    val document: StudyDocument? = null, val selectedChapterIds: Set<String> = emptySet(), val quizId: String? = null, val question: QuizQuestion? = null,
    val documentLibrary: List<StudyDocument>? = null,
    val documentRepairNotice: String? = null,
    val savedInterests: List<String>? = null, val interestDraft: List<String> = emptyList(), val interestSaveMessage: String? = null,
    val feedback: Feedback? = null, val results: Results? = null,
    val canResumeMastery: Boolean = false,
    val canResumeDocumentQuiz: Boolean = false,
    val documentQuestionTotal: Int = 10,
    val documentQuestionCountInput: String = "10",
    val documentDifficulty: String = "easy", val savedQuizDifficulty: String? = null,
    val documentQuestionType: String = "multiple_choice", val savedQuizQuestionType: String? = null,
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
        canResumeDocumentQuiz = preferences.contains("active_document_quiz:${preferences.getString("email", "").orEmpty().lowercase()}") ||
            preferences.contains("active_document:${preferences.getString("email", "").orEmpty().lowercase()}"),
    ))
    val state: StateFlow<AppUiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            val restored = withContext(Dispatchers.IO) { runCatching { tokenStore.read() } }
            api.restoreToken(restored.getOrNull())
            mutableState.value = mutableState.value.copy(loading = false,
                screen = if (api.hasToken) (if (savedGrade == null) Screen.Grade else Screen.Subjects) else Screen.SignIn,
                error = if (restored.isFailure) "Unable to restore the saved session. Please sign in." else null)
            if (api.hasToken && preferences.getString(activeFlowKey(), null) == "document" && mutableState.value.canResumeDocumentQuiz) resumeDocumentQuiz()
            else if (api.hasToken && preferences.contains(activeSessionKey())) resumeLearning()
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
    private fun documentQuizKey() = "active_document_quiz:${mutableState.value.accountEmail.lowercase()}"
    private fun documentKey() = "active_document:${mutableState.value.accountEmail.lowercase()}"
    private fun documentChapterKey() = "active_document_chapter:${mutableState.value.accountEmail.lowercase()}"
    private fun documentCountKey() = "document_question_count:${mutableState.value.accountEmail.lowercase()}"
    private fun documentDifficultyKey() = "document_difficulty:${mutableState.value.accountEmail.lowercase()}"
    private fun documentQuestionTypeKey() = "document_question_type:${mutableState.value.accountEmail.lowercase()}"
    private fun pendingQuizCreationKey() = "pending_quiz_creation:${mutableState.value.accountEmail.lowercase()}"
    private fun activeFlowKey() = "active_flow:${mutableState.value.accountEmail.lowercase()}"

    fun resumeDocumentQuiz() {
        val id = preferences.getString(documentQuizKey(), null)
        if (id == null) {
            resumeUploadedDocument()
            return
        }
        perform(null) {
            val resumed = try { api.resumeDocumentQuiz(id) } catch (failure: ApiFailure) {
                if (failure.status == 404) {
                    preferences.edit().remove(documentQuizKey()).apply()
                    mutableState.value = mutableState.value.copy(canResumeDocumentQuiz = false, screen = Screen.Subjects)
                }
                throw failure
            }
            preferences.edit().putString(activeFlowKey(), "document").apply()
            val completed = resumed.question == null
            mutableState.value = mutableState.value.copy(document = resumed.document, quizId = id,
                documentQuestionTotal = resumed.total, savedQuizDifficulty = resumed.difficulty, savedQuizQuestionType = resumed.questionType, question = resumed.question, feedback = resumed.feedback,
                results = if (completed) api.results(id) else null, canResumeDocumentQuiz = true,
                screen = if (completed) Screen.Results else if (resumed.feedback != null) Screen.Feedback else Screen.Question)
        }
    }

    private fun resumeUploadedDocument() {
        val id = preferences.getString(documentKey(), null) ?: return
        perform(null) {
            val document = try { api.getDocument(id) } catch (failure: ApiFailure) {
                if (failure.status == 404) {
                    preferences.edit().remove(documentKey()).remove(documentChapterKey()).apply()
                    mutableState.value = mutableState.value.copy(canResumeDocumentQuiz = false, screen = Screen.Home)
                }
                throw failure
            }
            val saved = preferences.getString(documentChapterKey(), null)
            val savedIds = saved?.let { value ->
                if (value.startsWith("[")) runCatching { JSONArray(value).let { array -> (0 until array.length()).map(array::getString).toSet() } }.getOrDefault(emptySet())
                else setOf(value) // Migrate the previous single-chapter preference.
            }
            val chapters = restoredChapterSelection(savedIds, document.chapters.map { it.id })
            preferences.edit().putString(activeFlowKey(), "document").apply()
            mutableState.value = mutableState.value.copy(document = document, selectedChapterIds = chapters,
                documentQuestionCountInput = preferences.getString(documentCountKey(), "10") ?: "10",
                documentDifficulty = restoredDocumentDifficulty(preferences.getString(documentDifficultyKey(), null)), savedQuizDifficulty = null,
                documentQuestionType = restoredDocumentQuestionType(preferences.getString(documentQuestionTypeKey(), null)), savedQuizQuestionType = null,
                quizId = null, question = null, feedback = null, results = null,
                canResumeDocumentQuiz = true, screen = Screen.Chapters)
        }
    }

    fun resumeLearning() {
        val sessionId = preferences.getString(activeSessionKey(), null) ?: return
        perform(null) {
            val resumed = api.resumeMastery(sessionId)
            preferences.edit().putString(activeFlowKey(), "mastery").apply()
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
            canResumeMastery = preferences.contains("active_mastery:${email.lowercase()}"),
            canResumeDocumentQuiz = preferences.contains("active_document_quiz:${email.lowercase()}") || preferences.contains("active_document:${email.lowercase()}"))
    }
    fun selectGrade(grade: Int) { preferences.edit().putInt("grade", grade).apply(); mutableState.value = mutableState.value.copy(grade = grade, screen = Screen.Subjects, progressSnapshot = null, unlockedChapterIds = emptySet()); refreshProgress() }
    fun selectSubject(subject: LearningSubject) { mutableState.value = mutableState.value.copy(subject = subject, screen = Screen.MasteryChapters) }
    fun selectMasteryChapter(chapter: MasteryChapter) {
        val current = mutableState.value
        val chapterKey = "${current.subject?.id}:${chapter.id}"
        if (chapter.locked && chapterKey !in current.unlockedChapterIds) return
        perform(null) {
            val started = api.startDiagnostic(current.grade ?: 6, requireNotNull(current.subject).id, chapter.id)
            preferences.edit().putString(activeSessionKey(), started.id).putString(activeFlowKey(), "mastery").apply()
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
        perform(null, SubmittedFlow.MASTERY) {
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
        perform(null, SubmittedFlow.MASTERY) {
            val outcome = api.submitPractice(requireNotNull(current.masterySessionId), answer)
            mutableState.value = current.copy(practiceResult = outcome.first, showHint = !outcome.first, error = null)
        }
    }
    fun moveToRewrite() { mutableState.value = mutableState.value.copy(screen = Screen.Rewrite, rewrite = "") }
    fun updateRewrite(value: String) { mutableState.value = mutableState.value.copy(rewrite = value) }
    fun submitRewrite() {
        val current = mutableState.value
        perform(null, SubmittedFlow.MASTERY) {
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
    fun openInterests() {
        mutableState.value = mutableState.value.copy(screen = Screen.Interests, savedInterests = null, interestDraft = emptyList(), interestSaveMessage = null)
        reloadInterests()
    }
    fun reloadInterests() = perform(null) {
        val saved = api.getInterests()
        mutableState.value = mutableState.value.copy(savedInterests = saved, interestDraft = saved, interestSaveMessage = null)
    }
    fun selectInterest(interest: String) {
        val current = mutableState.value
        if (current.loading || current.savedInterests == null) return
        mutableState.value = current.copy(interestDraft = toggleInterest(current.interestDraft, interest), interestSaveMessage = null)
    }
    fun clearInterests() {
        if (!mutableState.value.loading) mutableState.value = mutableState.value.copy(interestDraft = emptyList(), interestSaveMessage = null)
    }
    fun saveInterests() = perform(null) {
        check(mutableState.value.savedInterests != null)
        val saved = api.saveInterests(mutableState.value.interestDraft)
        mutableState.value = mutableState.value.copy(savedInterests = saved, interestDraft = saved, interestSaveMessage = "Interests saved")
    }
    fun setDarkMode(enabled: Boolean) { preferences.edit().putBoolean("dark_mode", enabled).apply(); mutableState.value = mutableState.value.copy(darkMode = enabled) }
    fun signOut() = perform(Screen.SignIn) { tokenStore.clear(); api.signOut(); preferences.edit().remove("email").remove("grade").remove("unlocked").apply(); mutableState.value = AppUiState(darkMode = mutableState.value.darkMode) }
    fun deleteAccount() = perform(null) { api.deleteAccount(); tokenStore.clear(); preferences.edit().clear().apply(); mutableState.value = AppUiState() }
    fun changeGrade() { mutableState.value = mutableState.value.copy(screen = Screen.Grade) }
    fun backToSubjects() { mutableState.value = mutableState.value.copy(screen = Screen.Subjects) }
    fun startDocumentStudy() { mutableState.value = mutableState.value.copy(screen = Screen.Home) }

    fun openDocumentLibrary() {
        mutableState.value = mutableState.value.copy(screen = Screen.DocumentLibrary, documentLibrary = null)
        refreshDocumentLibrary()
    }
    fun refreshDocumentLibrary() = perform(null) {
        mutableState.value = mutableState.value.copy(documentLibrary = api.listDocuments())
    }
    fun openSavedDocument(id: String) = perform(Screen.Chapters) {
        // Revalidate ownership/existence instead of trusting a potentially stale list.
        rememberUploadedDocument(api.getDocument(id))
    }
    fun deleteDocument(id: String) = perform(null) {
        try { api.deleteDocument(id) } catch (failure: ApiFailure) {
            if (failure.status != 404) throw failure // Already removed on another device.
        }
        val current = mutableState.value
        val clearsActive = current.document?.id == id || preferences.getString(documentKey(), null) == id
        if (clearsActive) {
            preferences.edit().remove(documentKey()).remove(documentChapterKey()).remove(documentQuizKey()).remove(pendingQuizCreationKey()).apply()
        }
        mutableState.value = stateAfterDocumentDeletion(current, id).let {
            if (clearsActive) it.copy(canResumeDocumentQuiz = false) else it
        }
    }

    fun upload(context: Context, uri: Uri) = perform(Screen.Chapters) {
        rememberUploadedDocument(api.upload(context.contentResolver, uri))
    }
    private fun rememberUploadedDocument(document: StudyDocument) {
        val chapter = document.chapters.firstOrNull()?.id
        check(preferences.edit().putString(documentKey(), document.id).putString(documentChapterKey(), chapter)
            .remove(documentQuizKey()).putString(activeFlowKey(), "document").commit())
        mutableState.value = mutableState.value.copy(document = document, documentRepairNotice = null, selectedChapterIds = setOfNotNull(chapter),
            documentQuestionCountInput = preferences.getString(documentCountKey(), "10") ?: "10",
            documentDifficulty = restoredDocumentDifficulty(preferences.getString(documentDifficultyKey(), null)), savedQuizDifficulty = null,
            documentQuestionType = restoredDocumentQuestionType(preferences.getString(documentQuestionTypeKey(), null)), savedQuizQuestionType = null,
            quizId = null, question = null, feedback = null, results = null, canResumeDocumentQuiz = true)
    }
    fun selectChapter(chapterId: String) {
        if (mutableState.value.loading) return
        if (mutableState.value.document?.chapters?.none { it.id == chapterId } != false) return
        val selected = mutableState.value.selectedChapterIds
        saveChapterSelection(if (chapterId in selected) selected - chapterId else selected + chapterId)
    }
    fun selectAllDocumentChapters() = saveChapterSelection(mutableState.value.document?.chapters?.map { it.id }?.toSet().orEmpty())
    fun clearDocumentChapters() = saveChapterSelection(emptySet())
    private fun saveChapterSelection(ids: Set<String>) {
        if (mutableState.value.loading) return
        preferences.edit().putString(documentChapterKey(), JSONArray(ids.toList()).toString()).apply()
        mutableState.value = mutableState.value.copy(selectedChapterIds = ids)
    }
    fun setDocumentQuestionCount(input: String) {
        if (mutableState.value.loading || input.length > 3) return
        preferences.edit().putString(documentCountKey(), input).apply()
        mutableState.value = mutableState.value.copy(documentQuestionCountInput = input)
    }
    fun setDocumentDifficulty(value: String) {
        if (mutableState.value.loading || value !in documentDifficulties) return
        preferences.edit().putString(documentDifficultyKey(), value).apply()
        mutableState.value = mutableState.value.copy(documentDifficulty = value)
    }
    fun setDocumentQuestionType(value: String) {
        if (mutableState.value.loading || value !in documentQuestionTypes) return
        preferences.edit().putString(documentQuestionTypeKey(), value).apply()
        mutableState.value = mutableState.value.copy(documentQuestionType = value)
    }
    fun repairDocumentStructure() = perform(null) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        // No selection/settings or pending creation identity changes. Retrying this
        // idempotent operation is safe even if the prior response was lost.
        mutableState.value = stateAfterStructureRepair(current, api.repairDocumentStructure(document.id))
    }
    fun createQuiz() = perform(null) {
        val current = mutableState.value
        require(current.selectedChapterIds.isNotEmpty()) { "Select at least one chapter" }
        val count = requireNotNull(validDocumentQuestionCount(current.documentQuestionCountInput)) { "Choose 5 to 20 questions" }
        val documentId = requireNotNull(current.document).id
        val chapterIds = current.selectedChapterIds.sorted()
        val fingerprint = quizCreationFingerprint(documentId, chapterIds, count, current.documentDifficulty, current.documentQuestionType)
        val pendingKey = pendingQuizCreationKey()
        val requestId = prepareQuizCreation(preferences.getString(pendingKey, null), fingerprint,
            persist = { preferences.edit().putString(pendingKey, it).commit() })
        val quiz = api.createQuiz(documentId, chapterIds, count, current.documentDifficulty, current.documentQuestionType, requestId)
        val resumed = api.resumeDocumentQuiz(quiz.id)
        check(resumed.document.id == documentId && resumed.total == count) { "Recovered quiz does not match the request" }
        validateDocumentFormat(current.documentQuestionType, resumed.questionType)
        val completed = resumed.question == null
        val results = if (completed) api.results(quiz.id) else null
        check(preferences.edit().putString(documentQuizKey(), quiz.id).putString(activeFlowKey(), "document")
            .remove(documentKey()).remove(documentChapterKey()).remove(pendingKey).commit())
        mutableState.value = current.copy(quizId = quiz.id, question = resumed.question, feedback = resumed.feedback, results = results,
            documentQuestionTotal = resumed.total, savedQuizDifficulty = resumed.difficulty, savedQuizQuestionType = resumed.questionType,
            canResumeDocumentQuiz = true, screen = if (completed) Screen.Results else if (resumed.feedback != null) Screen.Feedback else Screen.Question)
    }
    fun submitAnswer(option: String) = perform(Screen.Feedback, SubmittedFlow.DOCUMENT) { val current = mutableState.value; mutableState.value = current.copy(feedback = api.answer(requireNotNull(current.quizId), requireNotNull(current.question).id, option)) }
    fun continueAfterFeedback() { val current = mutableState.value; val feedback = current.feedback ?: return; if (feedback.next != null) mutableState.value = current.copy(screen = Screen.Question, question = feedback.next, feedback = null) else loadResults() }
    fun loadResults() = perform(Screen.Results) { mutableState.value = mutableState.value.copy(results = api.results(requireNotNull(mutableState.value.quizId))) }
    fun startAnotherDocument() { preferences.edit().remove(documentQuizKey()).remove(documentKey()).remove(documentChapterKey()).remove(pendingQuizCreationKey()).apply(); mutableState.value = mutableState.value.copy(screen = Screen.Home, document = null, selectedChapterIds = emptySet(), quizId = null, question = null, feedback = null, results = null, canResumeDocumentQuiz = false) }
    fun clearError() { mutableState.value = mutableState.value.copy(error = null) }

    private var operationInFlight = false
    private fun perform(destination: Screen?, submittedFlow: SubmittedFlow? = null, block: suspend () -> Unit) = viewModelScope.launch {
        if (operationInFlight) return@launch
        operationInFlight = true
        var resumeAfterConflict: SubmittedFlow? = null
        mutableState.value = mutableState.value.copy(loading = true, error = null)
        try {
            withContext(Dispatchers.IO) { block() }
            mutableState.value = mutableState.value.copy(screen = destination ?: mutableState.value.screen, loading = false)
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: Exception) {
            val recovery = recoveryAfterFailure((failure as? ApiFailure)?.status, submittedFlow)
            if (failure is ApiFailure && failure.sessionExpired) {
                api.signOut()
                val cleared = withContext(Dispatchers.IO) { runCatching { tokenStore.clear() } }.isSuccess
                // Keep account-scoped resume pointers. Reauthentication can restore server progress.
                mutableState.value = AppUiState(darkMode = mutableState.value.darkMode,
                    error = if (cleared) failure.message else "Your session is invalid. Saved credentials could not be cleared. Please sign in again.")
            } else if (recovery != null) {
                resumeAfterConflict = recovery
                mutableState.value = mutableState.value.copy(loading = false)
            } else {
                val message = when (failure) {
                    is ApiFailure -> failure.message
                    is DocumentUploadException -> failure.message
                    is IOException -> "Could not reach the learning service. Check your connection and try again."
                    else -> "Something went wrong. Please try again."
                }
                mutableState.value = mutableState.value.copy(loading = false, error = message)
            }
        } finally {
            operationInFlight = false
        }
        when (resumeAfterConflict) {
            SubmittedFlow.MASTERY -> resumeLearning()
            SubmittedFlow.DOCUMENT -> resumeDocumentQuiz()
            null -> Unit
        }
    }
}

private class LearningApi(initialToken: String?, private val saveToken: (String) -> Unit) {
    private val masterySubmissionState = MasterySubmissionState()
    private var token: String? = initialToken; private val baseUrl = BuildConfig.API_BASE_URL
    val hasToken: Boolean get() = token != null
    fun restoreToken(value: String?) { token = value }
    private fun acceptToken(response: JSONObject) { val accepted = response.getString("access_token"); saveToken(accepted); masterySubmissionState.clear(); token = accepted }
    fun register(email: String, password: String) = acceptToken(request("POST", "/v1/auth/register", JSONObject().put("email", email).put("password", password).toString()))
    fun login(email: String, password: String) = acceptToken(request("POST", "/v1/auth/login", JSONObject().put("email", email).put("password", password).toString()))
    fun signOut() { token = null; masterySubmissionState.clear() }
    fun deleteAccount() { requestNoContent("DELETE", "/v1/account"); signOut() }
    fun getInterests(): List<String> = request("GET", "/v1/account", null).getJSONArray("interests").strings()
    fun saveInterests(values: List<String>): List<String> = request("PUT", "/v1/account/interests",
        JSONObject().put("interests", JSONArray(values)).toString()).getJSONArray("interests").strings()
    fun upload(resolver: ContentResolver, uri: Uri): StudyDocument {
        var originalName = "study-material.txt"
        var declaredSize: Long? = null
        resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME, android.provider.OpenableColumns.SIZE), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                val sizeIndex = cursor.getColumnIndex(android.provider.OpenableColumns.SIZE)
                if (nameIndex >= 0 && !cursor.isNull(nameIndex)) originalName = cursor.getString(nameIndex)
                if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) declaredSize = cursor.getLong(sizeIndex)
            }
        }
        validateDocumentSize(declaredSize)
        val name = safeDocumentName(originalName)
        val mediaType = documentMediaType(name)
        val boundary = "Learnly-${UUID.randomUUID()}"
        val connection = connection("POST", "/v1/documents", "multipart/form-data; boundary=$boundary")
        connection.setChunkedStreamingMode(16 * 1024)
        try {
            resolver.openInputStream(uri)?.use { input ->
                BufferedOutputStream(connection.outputStream).use { output ->
                    output.write("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"$name\"\r\nContent-Type: $mediaType\r\n\r\n".toByteArray(Charsets.UTF_8))
                    copyDocument(input, output)
                    output.write("\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8))
                }
            } ?: throw DocumentUploadException("The selected file could not be read. Please select it again.")
            return document(readJson(connection))
        } finally { connection.disconnect() }
    }
    fun getDocument(id: String): StudyDocument = document(request("GET", "/v1/documents/$id", null))
    fun repairDocumentStructure(id: String): StudyDocument = document(request("POST", "/v1/documents/$id/structure/repair", null))
    fun deleteDocument(id: String) { requestNoContent("DELETE", "/v1/documents/$id") }
    fun listDocuments(): List<StudyDocument> {
        val response = JSONArray(readApiResponse(connection("GET", "/v1/documents", "application/json")))
        return (0 until response.length()).map { document(response.getJSONObject(it)) }
    }
    data class StartedDocumentQuiz(val id: String, val question: QuizQuestion, val total: Int, val difficulty: String?, val questionType: String?)
    fun createQuiz(documentId: String, chapterIds: List<String>, count: Int, difficulty: String, questionType: String, requestId: String): StartedDocumentQuiz {
        val response = request("POST", "/v1/documents/$documentId/quizzes", JSONObject().put("chapter_ids", JSONArray(chapterIds)).put("question_count", count).put("difficulty", difficulty).put("question_type", questionType).put("request_id", requestId).toString())
        val returnedType = if (response.isNull("question_type")) null else response.getString("question_type")
        validateDocumentFormat(questionType, returnedType)
        val first = question(response.getJSONObject("first_question"))
        validateDocumentOptions(returnedType, first.options)
        return StartedDocumentQuiz(response.getString("id"), first, response.getInt("question_count"), if (response.isNull("difficulty")) null else response.getString("difficulty"), returnedType)
    }
    data class ResumedDocumentQuiz(val document: StudyDocument, val total: Int, val question: QuizQuestion?, val feedback: Feedback?, val difficulty: String?, val questionType: String?)
    fun resumeDocumentQuiz(id: String): ResumedDocumentQuiz {
        val response = request("GET", "/v1/quizzes/$id", null)
        val feedback = response.optJSONObject("last_feedback")?.let { value -> Feedback(value.getBoolean("correct"), value.getString("selected_option"), value.getString("correct_option"), value.getString("explanation"), value.getString("source_reference"), value.optJSONObject("next_question")?.let(::question)) }
        val returnedType = if (response.isNull("question_type")) null else response.getString("question_type")
        require(returnedType == null || returnedType in documentQuestionTypes) { "Unsupported saved quiz format" }
        val pending = response.optJSONObject("question")?.let(::question)
        pending?.let { validateDocumentOptions(returnedType, it.options) }
        feedback?.next?.let { validateDocumentOptions(returnedType, it.options) }
        return ResumedDocumentQuiz(document(response.getJSONObject("document")), response.getInt("total"), pending, feedback, if (response.isNull("difficulty")) null else response.getString("difficulty"), returnedType)
    }
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
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            ResumedMastery(response.getInt("grade"), response.getString("subject_id"), response.getString("chapter_id"), response.getString("status"), question?.let(::adaptiveQuestion), question?.getInt("ordinal") ?: 1, question?.getInt("total") ?: 3, tutor, if (response.isNull("selected_option")) null else response.getString("selected_option"), (response.getDouble("mastery_score") * 100).toInt(), response.getInt("coaching_rounds"), if (response.isNull("assessment_points")) null else response.getInt("assessment_points"), if (response.isNull("assessment_feedback")) null else response.getString("assessment_feedback"))
        }
    }
    fun startDiagnostic(grade: Int, subjectId: String, chapterId: String): StartedDiagnostic {
        val response = request("POST", "/v1/mastery/diagnostics", JSONObject().put("grade", grade).put("subject_id", subjectId).put("chapter_id", chapterId).toString())
        val question = response.getJSONObject("question")
        return masterySubmissionState.accept(response.getString("id"), response.getString("state_token")) {
            StartedDiagnostic(response.getString("id"), adaptiveQuestion(question), question.getInt("ordinal"), question.getInt("total"))
        }
    }
    fun answerDiagnostic(sessionId: String, selected: String): DiagnosticResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/diagnostic-answer", JSONObject().put("selected_option", selected).toString())
        val next = response.optJSONObject("next_question")
        val tutor = response.optJSONObject("tutor")?.let { TutorLesson(it.getString("title"), it.getString("explanation"), it.getString("worked_example"), it.getString("hint"), it.getString("practice_prompt")) }
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            DiagnosticResult(response.getBoolean("correct"), response.getString("next_action"), next?.let(::adaptiveQuestion), next?.optInt("ordinal") ?: 1, (response.getDouble("mastery_score") * 100).toInt(), tutor)
        }
    }
    fun submitPractice(sessionId: String, answer: String): Pair<Boolean, String?> {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/practice", JSONObject().put("response", answer).toString())
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            response.getBoolean("correct") to response.optString("hint").takeIf(String::isNotBlank)
        }
    }
    fun submitRewrite(sessionId: String, rewrite: String): RewriteResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/rewrite", JSONObject().put("response", rewrite).toString())
        val next = response.optJSONObject("next_question")
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            RewriteResult(response.getBoolean("mastery_achieved"), (response.getDouble("mastery_score") * 100).toInt(),
            response.getString("confidence").replace('_', ' ').replaceFirstChar(Char::uppercase),
            if (response.isNull("coaching")) null else response.getString("coaching"), response.getString("next_action"),
            next?.let(::adaptiveQuestion), next?.getInt("ordinal"),
            if (response.isNull("assessment_points")) null else response.getInt("assessment_points"),
            if (response.isNull("assessment_feedback")) null else response.getString("assessment_feedback"))
        }
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
    fun progressWithWeekly(grade: Int): ProgressSnapshot { val dashboard = progressDashboard(grade); val weekly = weeklyReport(grade); return dashboard.copy(questionsAnswered = weekly.questionsAnswered, accuracy = weekly.accuracy, masteredChapters = weekly.masteredChapters, examReadiness = weekly.examReadiness, readinessLabel = weekly.readinessLabel) }
    private fun request(method: String, path: String, body: String?): JSONObject {
        val sessionId = Regex("^/v1/mastery/sessions/([^/]+)(?:/(diagnostic-answer|practice|rewrite))?$")
            .matchEntire(path)?.groupValues?.get(1)
        val guardedBody = if (method == "POST" && sessionId != null) {
            JSONObject(requireNotNull(body)).put("expected_state", masterySubmissionState.expected(sessionId)).toString()
        } else body
        val connection = connection(method, path, "application/json")
        try {
            if (guardedBody != null) connection.outputStream.use { it.write(guardedBody.toByteArray(Charsets.UTF_8)) }
            // Transport success alone does not acknowledge a learning transition.
            // Each adaptive decoder accepts its token only after constructing its result.
            return readJson(connection, path.startsWith("/v1/auth/"))
        } finally { connection.disconnect() }
    }
    private fun requestNoContent(method: String, path: String) { readApiResponse(connection(method, path, "application/json")) }
    private fun connection(method: String, path: String, contentType: String): HttpURLConnection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply { requestMethod = method; instanceFollowRedirects = false; connectTimeout = 15_000; readTimeout = if (method == "POST" && path.endsWith("/quizzes")) 135_000 else 30_000; doInput = true; setRequestProperty("Content-Type", contentType); token?.let { setRequestProperty("Authorization", "Bearer $it") }; if (method == "POST" || method == "PUT" || method == "PATCH") doOutput = true }
    private fun readJson(connection: HttpURLConnection, authenticationRequest: Boolean = false): JSONObject = JSONObject(readApiResponse(connection, authenticationRequest))
    private fun document(value: JSONObject) = StudyDocument(value.getString("id"), value.getString("original_name"), value.getJSONArray("chapters").let { array -> (0 until array.length()).map { index -> array.getJSONObject(index).let { Chapter(it.getString("id"), it.getString("title"), it.getDouble("confidence").toFloat()) } } })
    private fun question(value: JSONObject): QuizQuestion {
        val options = value.getJSONArray("options").strings()
        validateDocumentOptions(if (value.isNull("question_type")) null else value.getString("question_type"), options)
        return QuizQuestion(value.getString("id"), value.getInt("ordinal"), value.getString("prompt"), options, value.getString("source_reference"))
    }
    private fun adaptiveQuestion(value: JSONObject) = DiagnosticQuestion(value.getString("prompt"), value.getJSONArray("options").strings(), "")
    private fun JSONArray.toQuestionList(): List<QuizQuestion> = (0 until length()).map { question(getJSONObject(it)) }
    private fun JSONArray.strings(): List<String> = (0 until length()).map(::getString)
}
