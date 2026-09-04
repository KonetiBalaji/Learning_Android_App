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
data class GuardianAccount(val id: String, val email: String, val linkedAt: String)
data class CurriculumCatalogClient(val version: String, val grade: Int, val board: String,
                                   val subjects: List<LearningSubject>, val chapters: Map<String, List<MasteryChapter>>)

data class LearningSubject(val id: String, val title: String, val icon: String, val progress: Int, val accent: Long)
data class MasteryChapter(val id: String, val title: String, val progress: Int, val locked: Boolean = false)
data class DiagnosticQuestion(val prompt: String, val options: List<String>, val correct: String)
data class TutorLesson(val title: String, val explanation: String, val workedExample: String, val hint: String, val practicePrompt: String)
data class ProgressSnapshot(
    val subjects: Map<String, Int>, val weakAreas: List<String>, val recommendations: List<String>,
    val questionsAnswered: Int = 0, val accuracy: Int = 0, val masteredChapters: Int = 0,
    val examReadiness: Int = 0, val readinessLabel: String = "Needs support",
    val chapterScores: Map<String, Int> = emptyMap(), val masteredChapterIds: Set<String> = emptySet(),
    val unlockedChapterIds: Set<String> = emptySet(),
    val weeklyObservedStudySeconds: Long? = null,
)

sealed interface Screen {
    data object SignIn : Screen; data object Grade : Screen; data object Subjects : Screen; data object MasteryChapters : Screen
    data object Diagnostic : Screen; data object Tutor : Screen; data object TutorChat : Screen; data object Practice : Screen; data object Rewrite : Screen
    data object Mastery : Screen; data object ParentDashboard : Screen; data object GuardianAccess : Screen; data object Home : Screen; data object Chapters : Screen
    data object Question : Screen; data object Feedback : Screen; data object Results : Screen; data object Settings : Screen
    data object DocumentLibrary : Screen
    data object Interests : Screen
    data object DocumentPreview : Screen
}

val fractionQuestions = listOf(
    DiagnosticQuestion("What is 3/4 + 1/4?", listOf("1/2", "1", "3/8", "2"), "1"),
    DiagnosticQuestion("Which fraction is equal to 1/2?", listOf("2/6", "3/6", "4/6", "5/6"), "3/6"),
    DiagnosticQuestion("What is 5/8 - 1/8?", listOf("4/8", "4/16", "5/7", "6/8"), "4/8"),
)

private val subjectPresentation = mapOf(
    "math" to ("∑" to 0xFF4F46E5), "science" to ("⚗" to 0xFF2563EB),
    "english" to ("Aa" to 0xFF10B981), "social" to ("◎" to 0xFFF59E0B),
)

fun validatedCatalog(value: CurriculumCatalogClient, requestedGrade: Int): CurriculumCatalogClient {
    require(value.version.isNotBlank() && value.version.length <= 100 && value.grade == requestedGrade)
    require(value.board == "unconfirmed")
    require(value.subjects.map { it.id } == listOf("math", "science", "english", "social"))
    require(value.chapters.keys == value.subjects.map { it.id }.toSet())
    value.subjects.forEach { subject ->
        require(subject.title.isNotBlank() && subjectPresentation.containsKey(subject.id))
        val chapters = requireNotNull(value.chapters[subject.id])
        require(chapters.isNotEmpty() && chapters.map { it.id }.distinct().size == chapters.size)
        require(chapters.all { it.id.isNotBlank() && it.title.isNotBlank() })
    }
    return value
}

data class AppUiState(
    val tutorTurns: List<TutorChatTurn> = emptyList(), val tutorQuestion: String = "",
    val pendingTutorQuestion: PendingTutorQuestion? = null,
    val tutorConversationContext: String? = null,
    val screen: Screen = Screen.SignIn, val loading: Boolean = false, val error: String? = null, val grade: Int? = null,
    val subject: LearningSubject? = null, val masteryChapter: MasteryChapter? = null, val diagnosticIndex: Int = 0, val diagnosticCorrect: Int = 0,
    val selectedDiagnosticAnswer: String? = null, val practiceResult: Boolean? = null, val showHint: Boolean = false, val coachingRound: Int = 0, val rewrite: String = "",
    val masterySessionId: String? = null, val adaptiveQuestion: DiagnosticQuestion? = null, val adaptiveOrdinal: Int = 1,
    val adaptiveTotal: Int = fractionQuestions.size, val tutorLesson: TutorLesson? = null, val masteryScore: Int = 0,
    val masteryConfidence: String = "Developing", val progressSnapshot: ProgressSnapshot? = null,
    val unlockedChapterIds: Set<String> = emptySet(), val darkMode: Boolean = false, val accountEmail: String = "",
    val document: StudyDocument? = null, val selectedChapterIds: Set<String> = emptySet(), val quizId: String? = null, val question: QuizQuestion? = null,
    val documentLibrary: List<StudyDocument>? = null,
    val uploadProgress: DocumentUploadProgress? = null,
    val documentRepairNotice: String? = null,
    val documentPreview: DocumentPreview? = null,
    val documentExcerpts: List<DocumentExcerpt> = emptyList(),
    val sourceQuery: String = "", val documentSearch: DocumentSearch? = null,
    val pdfPageDraft: PdfPageDraft? = null,
    val savedInterests: List<String>? = null, val interestDraft: List<String> = emptyList(), val interestSaveMessage: String? = null,
    val feedback: Feedback? = null, val results: Results? = null,
    val canResumeMastery: Boolean = false,
    val canResumeDocumentQuiz: Boolean = false,
    val documentQuestionTotal: Int = 10,
    val documentQuestionCountInput: String = "10",
    val documentDifficulty: String = "easy", val savedQuizDifficulty: String? = null,
    val documentQuestionType: String = "multiple_choice", val savedQuizQuestionType: String? = null,
    val assessmentPoints: Int? = null, val assessmentFeedback: String? = null,
    val catalogVersion: String? = null, val catalogBoard: String? = null,
    val catalogSubjects: List<LearningSubject> = emptyList(),
    val catalogChapters: Map<String, List<MasteryChapter>> = emptyMap(),
    val linkedLearners: List<GuardianAccount>? = null, val linkedGuardians: List<GuardianAccount>? = null,
    val guardianInvitationCode: String? = null, val guardianInvitationExpiresAt: String? = null,
    val guardianCodeDraft: String = "", val reportAccountEmail: String? = null,
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
    private val presenceSchedule = StudyPresenceSchedule()
    private var studyForeground = false
    private var lastStudyInteraction = 0L

    fun studyActivityResumed(resumed: Boolean) {
        studyForeground = resumed
        presenceSchedule.reset()
        if (resumed) studyInteraction()
    }
    fun studyInteraction() {
        val now = android.os.SystemClock.elapsedRealtime()
        if (now - lastStudyInteraction > 45_000) presenceSchedule.reset()
        lastStudyInteraction = now
    }

    init {
        viewModelScope.launch {
            while (true) {
                kotlinx.coroutines.delay(5_000)
                val snapshot = mutableState.value
                val observedAt = android.os.SystemClock.elapsedRealtime()
                val active = presenceEligible(studyForeground, snapshot.loading, snapshot.screen, observedAt, lastStudyInteraction)
                val command = presenceSchedule.next(if (active) snapshot.masterySessionId else null, observedAt) ?: continue
                try {
                    withContext(Dispatchers.IO) { api.reportStudyPresence(command.sessionId, command.reset) }
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (_: Exception) {
                    // Do not queue old observations or interrupt answer submission.
                    // The next successful request establishes a fresh interval.
                    presenceSchedule.reset()
                }
            }
        }
        viewModelScope.launch {
            val restored = withContext(Dispatchers.IO) { runCatching { tokenStore.read() } }
            api.restoreToken(restored.getOrNull())
            mutableState.value = mutableState.value.copy(loading = false,
                screen = if (api.hasToken) (if (savedGrade == null) Screen.Grade else Screen.Subjects) else Screen.SignIn,
                error = sessionRestoreError(restored.isFailure, tokenStore.lastReadFailed))
            if (api.hasToken && preferences.getString(activeFlowKey(), null) == "document" && mutableState.value.canResumeDocumentQuiz) resumeDocumentQuiz()
            else if (api.hasToken && preferences.contains(activeSessionKey())) resumeLearning()
            else if (api.hasToken && savedGrade != null) refreshProgress()
        }
    }

    private suspend fun loadProgress() {
        val grade = mutableState.value.grade ?: return
        val catalog = api.catalog(grade)
        val snapshot = api.progressDashboard(grade)
        mutableState.value = mutableState.value.copy(progressSnapshot = snapshot, unlockedChapterIds = snapshot.unlockedChapterIds,
            catalogVersion = catalog.version, catalogBoard = catalog.board, catalogSubjects = catalog.subjects, catalogChapters = catalog.chapters)
    }

    fun refreshProgress() = perform(null) { loadProgress() }

    private fun activeSessionKey() = "active_mastery:${mutableState.value.accountEmail.lowercase()}"
    private fun documentQuizKey() = "active_document_quiz:${mutableState.value.accountEmail.lowercase()}"
    private fun documentKey() = "active_document:${mutableState.value.accountEmail.lowercase()}"
    private fun documentChapterKey() = "active_document_chapter:${mutableState.value.accountEmail.lowercase()}"
    private fun documentExcerptKey(documentId: String) = "document_excerpts:$documentId:${mutableState.value.accountEmail.lowercase()}"
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
            mutableState.value = mutableState.value.copy(document = resumed.document, quizId = id, documentExcerpts = resumed.excerpts, sourceQuery = "", documentSearch = null, pdfPageDraft = null,
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
            val excerpts = decodeExcerpts(preferences.getString(documentExcerptKey(document.id), null))
            require(excerpts.isEmpty() || excerpts.map { it.chapterId }.toSet() == chapters) { "Saved excerpt selection does not match these chapters. Reopen the document to select again." }
            preferences.edit().putString(activeFlowKey(), "document").apply()
            mutableState.value = mutableState.value.copy(document = document, selectedChapterIds = chapters, documentExcerpts = excerpts, sourceQuery = "", documentSearch = null, pdfPageDraft = null,
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
            val catalog = api.catalog(resumed.grade)
            val subject = catalog.subjects.firstOrNull { it.id == resumed.subjectId }
                ?: error("The saved subject is not available in this version.")
            val chapter = catalog.chapters[subject.id]?.firstOrNull { it.id == resumed.chapterId }
                ?: error("The saved chapter is not available in this version.")
            mutableState.value = mutableState.value.copy(
                grade = resumed.grade, subject = subject, masteryChapter = chapter,
                catalogVersion = catalog.version, catalogBoard = catalog.board,
                catalogSubjects = catalog.subjects, catalogChapters = catalog.chapters,
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
        check(mutableState.value.screen == Screen.SignIn && !api.hasToken)
        finishAuthentication { api.passwordProfile(email, password, createAccount) }
    }
    fun authenticateGoogle(requestToken: suspend () -> String) = perform(Screen.Grade) {
        check(mutableState.value.screen == Screen.SignIn && !api.hasToken)
        val idToken = withContext(Dispatchers.Main) { requestToken() }
        finishAuthentication { api.googleProfile(idToken) }
    }
    private fun finishAuthentication(verifyProfile: () -> String) {
        val email = establishVerifiedSession(
            verifyProfile = verifyProfile,
            persist = { verifiedEmail ->
                check(preferences.edit().putString("email", verifiedEmail).remove("grade").remove("unlocked").commit())
                api.persistSession()
            },
            rollback = {
                api.signOut()
                tokenStore.clear()
                check(preferences.edit().remove("email").remove("grade").remove("unlocked").commit())
            },
        )
        mutableState.value = AppUiState(accountEmail = email, darkMode = mutableState.value.darkMode,
            canResumeMastery = preferences.contains("active_mastery:${email.lowercase()}"),
            canResumeDocumentQuiz = preferences.contains("active_document_quiz:${email.lowercase()}") || preferences.contains("active_document:${email.lowercase()}"))
    }
    fun selectGrade(grade: Int) {
        preferences.edit().putInt("grade", grade).apply()
        mutableState.value = mutableState.value.copy(grade = grade, screen = Screen.Subjects,
            progressSnapshot = null, unlockedChapterIds = emptySet(), subject = null, masteryChapter = null,
            catalogVersion = null, catalogBoard = null, catalogSubjects = emptyList(), catalogChapters = emptyMap())
        refreshProgress()
    }
    fun selectSubject(subject: LearningSubject) {
        if (mutableState.value.catalogSubjects.none { it.id == subject.id }) return
        mutableState.value = mutableState.value.copy(subject = subject, screen = Screen.MasteryChapters)
    }
    fun selectMasteryChapter(chapter: MasteryChapter) {
        val current = mutableState.value
        if (current.loading) return
        val chapterKey = "${current.subject?.id}:${chapter.id}"
        if (chapter.locked && chapterKey !in current.unlockedChapterIds) return
        perform(null) {
            val started = try {
                api.startDiagnostic(requireNotNull(current.grade), requireNotNull(current.subject).id, chapter.id)
            } catch (failure: ApiFailure) {
                if (failure.status != 403 || !chapter.locked) throw failure
                mutableState.value = stateAfterChapterAccessDenied(mutableState.value, chapterKey)
                throw ApiFailure(403, false, "This chapter is currently locked. Complete its prerequisite in this grade, then use Refresh progress. Your saved learning is unchanged.")
            }
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

    fun openTutorConversation() {
        if (mutableState.value.loading) return
        perform(Screen.TutorChat, SubmittedFlow.MASTERY) {
            val current = mutableState.value
            val sessionId = requireNotNull(current.masterySessionId)
            val context = api.tutorContext(sessionId)
            val turns = api.tutorHistory(sessionId)
            val sameContext = context == current.tutorConversationContext
            mutableState.value = current.copy(tutorTurns = turns, tutorConversationContext = context,
                tutorQuestion = if (sameContext) current.tutorQuestion else "",
                pendingTutorQuestion = pendingTutorQuestion(turns, if (sameContext) current.pendingTutorQuestion else null))
        }
    }

    fun changeTutorQuestion(value: String) {
        if (mutableState.value.screen == Screen.TutorChat && !mutableState.value.loading && mutableState.value.pendingTutorQuestion == null)
            mutableState.value = mutableState.value.copy(tutorQuestion = boundedTutorQuestion(value))
    }

    fun sendTutorQuestion() {
        val current = mutableState.value
        if (current.screen != Screen.TutorChat || current.loading) return
        val pending = current.pendingTutorQuestion ?: current.tutorQuestion.trim().takeIf { it.isNotBlank() }
            ?.let { PendingTutorQuestion(java.util.UUID.randomUUID().toString(), it) } ?: return
        perform(null, SubmittedFlow.MASTERY) {
            mutableState.value = mutableState.value.copy(pendingTutorQuestion = pending)
            val turn = api.askTutor(requireNotNull(current.masterySessionId), pending)
            mutableState.value = mutableState.value.copy(tutorTurns = mergeTutorTurn(current.tutorTurns, turn),
                pendingTutorQuestion = if (turn.status == "pending") pending else null, tutorQuestion = "")
        }
    }

    fun backFromTutorConversation() {
        if (!mutableState.value.loading) mutableState.value = mutableState.value.copy(screen = Screen.Tutor)
    }

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
            mutableState.value = current.copy(practiceResult = outcome.correct, showHint = !outcome.correct, error = null,
                tutorLesson = outcome.nextLesson ?: current.tutorLesson)
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
                tutorLesson = outcome.nextLesson ?: if (outcome.coaching == null) current.tutorLesson else current.tutorLesson?.copy(explanation = outcome.coaching),
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
        perform(null) { mutableState.value = current.copy(progressSnapshot = api.progressWithWeekly(current.grade ?: 8), reportAccountEmail = null, screen = Screen.ParentDashboard) }
    }
    fun openGuardianAccess() {
        mutableState.value = mutableState.value.copy(screen = Screen.GuardianAccess, linkedLearners = null, linkedGuardians = null,
            guardianInvitationCode = null, guardianInvitationExpiresAt = null, guardianCodeDraft = "")
        refreshGuardianAccess()
    }
    fun refreshGuardianAccess() = perform(null) {
        mutableState.value = mutableState.value.copy(linkedLearners = api.linkedLearners(), linkedGuardians = api.linkedGuardians())
    }
    fun createGuardianInvitation() = perform(null) {
        val invitation = api.createGuardianInvitation()
        mutableState.value = mutableState.value.copy(guardianInvitationCode = invitation.first,
            guardianInvitationExpiresAt = invitation.second)
    }
    fun updateGuardianCode(value: String) {
        mutableState.value = mutableState.value.copy(guardianCodeDraft = value.trim().take(128))
    }
    fun redeemGuardianCode() = perform(null) {
        api.redeemGuardianInvitation(mutableState.value.guardianCodeDraft)
        mutableState.value = mutableState.value.copy(guardianCodeDraft = "", linkedLearners = api.linkedLearners())
    }
    fun revokeGuardian(guardianId: String) = perform(null) {
        api.revokeGuardian(guardianId)
        mutableState.value = mutableState.value.copy(linkedGuardians = api.linkedGuardians(), guardianInvitationCode = null, guardianInvitationExpiresAt = null)
    }
    fun unlinkLearner(learnerId: String) = perform(null) {
        api.unlinkLearner(learnerId)
        mutableState.value = mutableState.value.copy(linkedLearners = api.linkedLearners())
    }
    fun openLinkedLearnerReport(learner: GuardianAccount) {
        val current = mutableState.value
        perform(null) { mutableState.value = current.copy(progressSnapshot = api.progressWithWeekly(current.grade ?: 8, learner.id),
            reportAccountEmail = learner.email, screen = Screen.ParentDashboard) }
    }
    fun backFromParentDashboard() {
        mutableState.value = mutableState.value.copy(screen = if (mutableState.value.reportAccountEmail == null) Screen.Subjects else Screen.GuardianAccess,
            reportAccountEmail = null)
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
    fun signOut() = perform(Screen.SignIn) {
        tokenStore.clear(); api.signOut(); preferences.edit().remove("email").remove("grade").remove("unlocked").apply()
        mutableState.value = AppUiState(darkMode = mutableState.value.darkMode, loading = true)
        mutableState.value = mutableState.value.copy(error = clearGoogleCredentialState(getApplication()))
    }
    fun deleteAccount() = perform(null) {
        api.deleteAccount(); tokenStore.clear(); preferences.edit().clear().apply()
        mutableState.value = AppUiState(loading = true)
        mutableState.value = mutableState.value.copy(error = clearGoogleCredentialState(getApplication()))
    }
    fun changeGrade() { mutableState.value = mutableState.value.copy(screen = Screen.Grade) }
    fun backToSubjects() {
        mutableState.value = mutableState.value.copy(screen = Screen.Subjects)
        if (mutableState.value.grade != null && mutableState.value.catalogSubjects.isEmpty()) refreshProgress()
    }
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
        preferences.edit().remove(documentExcerptKey(id)).apply()
        mutableState.value = stateAfterDocumentDeletion(current, id).let {
            if (clearsActive) it.copy(canResumeDocumentQuiz = false) else it
        }
    }

    fun upload(context: Context, uri: Uri) = perform(Screen.Chapters) {
        mutableState.value = mutableState.value.copy(uploadProgress = DocumentUploadProgress())
        try {
            rememberUploadedDocument(api.upload(context.contentResolver, uri) { progress ->
                mutableState.value = mutableState.value.copy(uploadProgress = progress)
            })
        } finally {
            mutableState.value = mutableState.value.copy(uploadProgress = null)
        }
    }
    private fun rememberUploadedDocument(document: StudyDocument) {
        val chapter = document.chapters.firstOrNull()?.id
        check(preferences.edit().putString(documentKey(), document.id).putString(documentChapterKey(), chapter)
            .remove(documentQuizKey()).remove(documentExcerptKey(document.id)).putString(activeFlowKey(), "document").commit())
        mutableState.value = mutableState.value.copy(document = document, documentRepairNotice = null, documentPreview = null, documentExcerpts = emptyList(), sourceQuery = "", documentSearch = null, pdfPageDraft = null, selectedChapterIds = setOfNotNull(chapter),
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
        val document = mutableState.value.document ?: return
        if (!preferences.edit().putString(documentChapterKey(), JSONArray(ids.toList()).toString()).remove(documentExcerptKey(document.id)).commit()) {
            mutableState.value = mutableState.value.copy(error = "Could not save chapter selection")
            return
        }
        mutableState.value = mutableState.value.copy(selectedChapterIds = ids, documentExcerpts = emptyList(), documentSearch = null, pdfPageDraft = null)
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
    fun previewDocumentChapter(chapterId: String, page: Int = 0) = perform(Screen.DocumentPreview) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        require(document.chapters.any { it.id == chapterId })
        val preview = api.previewDocumentChapter(document.id, chapterId, page)
        mutableState.value = current.copy(documentPreview = preview)
    }
    fun changePreviewPage(page: Int) {
        val preview = mutableState.value.documentPreview ?: return
        if (page in 0 until preview.totalPages) previewDocumentChapter(preview.chapterId, page)
    }
    fun closeDocumentPreview() {
        if (!mutableState.value.loading) mutableState.value = mutableState.value.copy(screen = Screen.Chapters, documentPreview = null)
    }
    fun addDocumentExcerpt(first: Int, last: Int) = perform(Screen.Chapters) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        val preview = requireNotNull(current.documentPreview)
        require(preview.documentId == document.id)
        saveConfirmedExcerpt(current, excerptFromSelection(preview, first, last))
    }
    private fun saveConfirmedExcerpt(current: AppUiState, excerpt: DocumentExcerpt) {
        saveConfirmedExcerpts(current, current.documentExcerpts + excerpt)
    }
    private fun saveConfirmedExcerpts(current: AppUiState, selected: List<DocumentExcerpt>) {
        val document = requireNotNull(current.document)
        val excerpts = canonicalExcerpts(selected)
        require(excerpts.isNotEmpty())
        val ids = excerpts.map { it.chapterId }.toSet()
        check(preferences.edit().putString(documentExcerptKey(document.id), encodeExcerpts(excerpts))
            .putString(documentChapterKey(), JSONArray(ids.toList()).toString()).commit()) { "Could not save excerpt selection" }
        mutableState.value = current.copy(documentExcerpts = excerpts, selectedChapterIds = ids, documentPreview = null, documentSearch = null, sourceQuery = "", pdfPageDraft = null)
    }
    fun loadPdfPages() = perform(null) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        require(document.name.endsWith(".pdf", ignoreCase = true)) { "Original page selection requires a PDF" }
        mutableState.value = current.copy(pdfPageDraft = null)
        val catalog = api.pdfPageCatalog(document.id)
        mutableState.value = current.copy(pdfPageDraft = PdfPageDraft(catalog))
    }
    fun setPdfPageInput(first: Boolean, value: String) {
        val current = mutableState.value
        val draft = current.pdfPageDraft ?: return
        if (current.loading || value.length > 4 || draft.catalog.documentId != current.document?.id) return
        mutableState.value = current.copy(pdfPageDraft = if (first) draft.copy(first = value, reviewed = null)
            else draft.copy(last = value, reviewed = null))
    }
    fun reviewPdfPages() = perform(null) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        val draft = requireNotNull(current.pdfPageDraft)
        require(draft.catalog.documentId == document.id)
        val range = requireNotNull(validPdfPageRange(draft.first, draft.last, draft.catalog.pages.size)) { "Choose a valid PDF page range" }
        mutableState.value = current.copy(pdfPageDraft = draft.copy(reviewed = null))
        val scope = api.resolvePdfPages(draft.catalog, range.first, range.second, document.chapters.map { it.id }.toSet())
        mutableState.value = current.copy(pdfPageDraft = draft.copy(reviewed = scope))
    }
    fun confirmPdfPages() = perform(Screen.Chapters) {
        val current = mutableState.value
        saveConfirmedExcerpts(current, confirmedPdfExcerpts(requireNotNull(current.pdfPageDraft), requireNotNull(current.document)))
    }
    fun setSourceQuery(value: String) {
        if (!mutableState.value.loading && value.length <= 240)
            mutableState.value = mutableState.value.copy(sourceQuery = value, documentSearch = null)
    }
    fun searchDocumentSource() = perform(null) {
        val current = mutableState.value
        require(validSourceQuery(current.sourceQuery)) { "Enter a phrase of 2 to 120 characters" }
        require(current.selectedChapterIds.isNotEmpty()) { "Choose chapters to search" }
        mutableState.value = current.copy(documentSearch = null)
        val result = api.searchDocumentSource(requireNotNull(current.document).id, current.selectedChapterIds, current.sourceQuery.trim())
        mutableState.value = current.copy(documentSearch = result)
    }
    fun useSourceSearchResult(index: Int) = perform(Screen.Chapters) {
        val current = mutableState.value
        val result = requireNotNull(current.documentSearch)
        require(result.query == current.sourceQuery.trim()) { "Search results are stale; search again" }
        saveConfirmedExcerpt(current, selectedSearchExcerpt(result, requireNotNull(current.document).id, current.selectedChapterIds, index))
    }
    fun repairDocumentStructure() = perform(null) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        // No selection/settings or pending creation identity changes. Retrying this
        // idempotent operation is safe even if the prior response was lost.
        mutableState.value = stateAfterStructureRepair(current, api.repairDocumentStructure(document.id)).copy(documentSearch = null, pdfPageDraft = null)
    }
    fun createQuiz() = perform(null) {
        val current = mutableState.value
        require(current.selectedChapterIds.isNotEmpty()) { "Select at least one chapter" }
        val count = requireNotNull(validDocumentQuestionCount(current.documentQuestionCountInput)) { "Choose 5 to 20 questions" }
        val documentId = requireNotNull(current.document).id
        val chapterIds = current.selectedChapterIds.sorted()
        require(current.documentExcerpts.isEmpty() || current.documentExcerpts.map { it.chapterId }.toSet() == current.selectedChapterIds)
        val fingerprint = quizCreationFingerprint(documentId, chapterIds, count, current.documentDifficulty, current.documentQuestionType, current.documentExcerpts)
        val pendingKey = pendingQuizCreationKey()
        val requestId = prepareQuizCreation(preferences.getString(pendingKey, null), fingerprint,
            persist = { preferences.edit().putString(pendingKey, it).commit() })
        val quiz = api.createQuiz(documentId, chapterIds, count, current.documentDifficulty, current.documentQuestionType, requestId, current.documentExcerpts)
        val resumed = api.resumeDocumentQuiz(quiz.id)
        check(resumed.document.id == documentId && resumed.total == count) { "Recovered quiz does not match the request" }
        validateDocumentFormat(current.documentQuestionType, resumed.questionType)
        check(resumed.excerpts == canonicalExcerpts(current.documentExcerpts)) { "Server did not preserve the selected excerpts. Update the backend before retrying." }
        val completed = resumed.question == null
        val results = if (completed) api.results(quiz.id) else null
        check(preferences.edit().putString(documentQuizKey(), quiz.id).putString(activeFlowKey(), "document")
            .remove(documentKey()).remove(documentChapterKey()).remove(documentExcerptKey(documentId)).remove(pendingKey).commit())
        mutableState.value = current.copy(quizId = quiz.id, question = resumed.question, feedback = resumed.feedback, results = results, sourceQuery = "", documentSearch = null, pdfPageDraft = null,
            documentQuestionTotal = resumed.total, savedQuizDifficulty = resumed.difficulty, savedQuizQuestionType = resumed.questionType,
            canResumeDocumentQuiz = true, screen = if (completed) Screen.Results else if (resumed.feedback != null) Screen.Feedback else Screen.Question)
    }
    fun submitAnswer(option: String) = perform(Screen.Feedback, SubmittedFlow.DOCUMENT) { val current = mutableState.value; mutableState.value = current.copy(feedback = api.answer(requireNotNull(current.quizId), requireNotNull(current.question).id, option)) }
    fun continueAfterFeedback() { val current = mutableState.value; val feedback = current.feedback ?: return; if (feedback.next != null) mutableState.value = current.copy(screen = Screen.Question, question = feedback.next, feedback = null) else loadResults() }
    fun loadResults() = perform(Screen.Results) { mutableState.value = mutableState.value.copy(results = api.results(requireNotNull(mutableState.value.quizId))) }
    fun startAnotherDocument() { preferences.edit().remove(documentQuizKey()).remove(documentKey()).remove(documentChapterKey()).remove(pendingQuizCreationKey()).apply(); mutableState.value = mutableState.value.copy(screen = Screen.Home, document = null, selectedChapterIds = emptySet(), documentExcerpts = emptyList(), documentPreview = null, sourceQuery = "", documentSearch = null, pdfPageDraft = null, quizId = null, question = null, feedback = null, results = null, canResumeDocumentQuiz = false) }
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
            mutableState.value = mutableState.value.copy(loading = false)
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
    fun tutorContext(sessionId: String): String = masterySubmissionState.expected(sessionId)
    fun tutorHistory(sessionId: String): List<TutorChatTurn> {
        val connection = connection("GET", "/v1/mastery/sessions/$sessionId/tutor-questions", "application/json")
        try {
            val response = JSONArray(readApiResponse(connection))
            return (0 until response.length()).map { tutorTurn(response.getJSONObject(it)) }
        } finally { connection.disconnect() }
    }

    fun askTutor(sessionId: String, pending: PendingTutorQuestion): TutorChatTurn {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/tutor-questions", JSONObject()
            .put("request_id", pending.requestId).put("question", pending.question)
            .put("expected_state", masterySubmissionState.expected(sessionId)).toString())
        return tutorTurn(response).also {
            require(it.requestId == pending.requestId && it.question == pending.question) { "Tutor acknowledgement did not match the question" }
        }
    }

    private fun tutorTurn(value: JSONObject): TutorChatTurn {
        val reply = value.optJSONObject("reply")
        return TutorChatTurn(value.getString("request_id"), value.getString("question"), value.getString("status"),
            reply?.getString("answer"), reply?.getBoolean("supported"))
    }
    private val masterySubmissionState = MasterySubmissionState()
    private var token: String? = initialToken; private val baseUrl = BuildConfig.API_BASE_URL
    val hasToken: Boolean get() = token != null
    fun restoreToken(value: String?) { token = value }
    fun passwordProfile(email: String, password: String, createAccount: Boolean): String {
        val path = if (createAccount) "/v1/auth/register" else "/v1/auth/login"
        return verifiedProfile(request("POST", path, JSONObject().put("email", email).put("password", password).toString()))
    }
    fun googleProfile(idToken: String): String {
        val response = try { request("POST", "/v1/auth/google", JSONObject().put("id_token", idToken).toString()) }
            catch (failure: ApiFailure) { throw googleExchangeFailure(failure.status) }
        return verifiedProfile(response)
    }
    private fun verifiedProfile(response: JSONObject): String {
        token = response.getString("access_token").also { require(it.isNotBlank()) }
        masterySubmissionState.clear()
        return request("GET", "/v1/account", null).getString("email").also { require(it.isNotBlank()) }
    }
    fun persistSession() { saveToken(requireNotNull(token)) }
    fun signOut() { token = null; masterySubmissionState.clear() }
    fun deleteAccount() { requestNoContent("DELETE", "/v1/account"); signOut() }
    fun getInterests(): List<String> = request("GET", "/v1/account", null).getJSONArray("interests").strings()
    fun catalog(grade: Int): CurriculumCatalogClient {
        val response = request("GET", "/v1/catalog?grade=$grade", null)
        val subjectsJson = response.getJSONArray("subjects")
        val subjects = mutableListOf<LearningSubject>()
        val chapters = linkedMapOf<String, List<MasteryChapter>>()
        for (index in 0 until subjectsJson.length()) {
            val item = subjectsJson.getJSONObject(index)
            val id = item.getString("id")
            val presentation = requireNotNull(subjectPresentation[id]) { "Unsupported catalog subject" }
            subjects += LearningSubject(id, item.getString("title"), presentation.first, 0, presentation.second)
            val values = item.getJSONArray("chapters")
            chapters[id] = (0 until values.length()).map { chapterIndex ->
                val chapter = values.getJSONObject(chapterIndex)
                MasteryChapter(chapter.getString("id"), chapter.getString("title"), 0,
                    locked = !chapter.isNull("prerequisite_id"))
            }
        }
        return validatedCatalog(CurriculumCatalogClient(response.getString("version"), response.getInt("grade"),
            response.getString("board"), subjects, chapters), grade)
    }
    fun createGuardianInvitation(): Pair<String, String> = request("POST", "/v1/guardian/invitations", "{}").let {
        it.getString("code") to it.getString("expires_at")
    }
    fun redeemGuardianInvitation(code: String): GuardianAccount = guardianAccount(request("POST", "/v1/guardian/links", JSONObject().put("code", code).toString()))
    fun linkedLearners(): List<GuardianAccount> = guardianAccounts(requestArray("GET", "/v1/guardian/learners"))
    fun linkedGuardians(): List<GuardianAccount> = guardianAccounts(requestArray("GET", "/v1/guardian/access"))
    fun unlinkLearner(id: String) = requestNoContent("DELETE", "/v1/guardian/learners/$id")
    fun revokeGuardian(id: String) = requestNoContent("DELETE", "/v1/guardian/access/$id")
    fun saveInterests(values: List<String>): List<String> = request("PUT", "/v1/account/interests",
        JSONObject().put("interests", JSONArray(values)).toString()).getJSONArray("interests").strings()
    fun upload(resolver: ContentResolver, uri: Uri, onProgress: (DocumentUploadProgress) -> Unit): StudyDocument {
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
        val knownSize = declaredSize?.takeIf { it > 0 }
        onProgress(DocumentUploadProgress(declaredBytes = knownSize))
        var copied = 0L
        var lastReported = 0L
        val name = safeDocumentName(originalName)
        val mediaType = documentMediaType(name)
        val boundary = "Learnly-${UUID.randomUUID()}"
        val connection = connection("POST", "/v1/documents", "multipart/form-data; boundary=$boundary")
        connection.setChunkedStreamingMode(16 * 1024)
        try {
            resolver.openInputStream(uri)?.use { input ->
                BufferedOutputStream(connection.outputStream).use { output ->
                    output.write("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"$name\"\r\nContent-Type: $mediaType\r\n\r\n".toByteArray(Charsets.UTF_8))
                    copied = copyDocument(input, output) { bytes ->
                        if (bytes - lastReported >= 256 * 1024 || bytes == knownSize) {
                            onProgress(DocumentUploadProgress(bytes, knownSize))
                            lastReported = bytes
                        }
                    }
                    output.write("\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8))
                }
            } ?: throw DocumentUploadException("The selected file could not be read. Please select it again.")
            onProgress(DocumentUploadProgress(copied, knownSize, awaitingAnalysis = true))
            return document(readJson(connection))
        } catch (failure: ApiFailure) {
            if (failure.status >= 500) throw uncertainUploadFailure()
            throw failure
        } catch (_: IOException) {
            throw uncertainUploadFailure()
        } catch (_: org.json.JSONException) {
            throw uncertainUploadFailure()
        } finally { connection.disconnect() }
    }
    fun getDocument(id: String): StudyDocument = document(request("GET", "/v1/documents/$id", null))
    fun reportStudyPresence(sessionId: String, reset: Boolean) {
        val value = request("POST", "/v1/mastery/sessions/$sessionId/presence?reset=$reset", null)
        require(value.getString("session_id") == sessionId && value.getLong("observed_study_seconds") >= 0)
    }
    fun previewDocumentChapter(documentId: String, chapterId: String, page: Int): DocumentPreview {
        val encoded = java.net.URLEncoder.encode(chapterId, "UTF-8").replace("+", "%20")
        val value = request("GET", "/v1/documents/$documentId/chapters/$encoded/preview?page=$page", null)
        return validateDocumentPreview(DocumentPreview(value.getString("document_id"), value.getString("chapter_id"),
            value.getString("title"), value.getInt("page"), value.getInt("total_pages"), value.getInt("start_character"),
            value.getInt("end_character"), value.getString("text")), documentId, chapterId, page)
    }
    fun repairDocumentStructure(id: String): StudyDocument = document(request("POST", "/v1/documents/$id/structure/repair", null))
    fun deleteDocument(id: String) { requestNoContent("DELETE", "/v1/documents/$id") }
    fun listDocuments(): List<StudyDocument> {
        val response = JSONArray(readApiResponse(connection("GET", "/v1/documents", "application/json")))
        return (0 until response.length()).map { document(response.getJSONObject(it)) }
    }
    fun pdfPageCatalog(documentId: String): PdfPageCatalog {
        val response = request("GET", "/v1/documents/$documentId/pdf-pages", null)
        val values = response.getJSONArray("pages")
        require(values.length() in 1..1000)
        val pages = (0 until values.length()).map { index ->
            val value = values.getJSONObject(index)
            fun integer(key: String): Int { val raw = value.get(key); require(raw is Int); return raw }
            val hasText = value.get("has_text"); require(hasText is Boolean)
            OriginalPdfPage(integer("page"), integer("start_character"), integer("end_character"), hasText)
        }
        return validatePdfPageCatalog(PdfPageCatalog(response.getString("document_id"), pages), documentId)
    }
    fun resolvePdfPages(catalog: PdfPageCatalog, first: Int, last: Int, chapterIds: Set<String>): PdfPageScope {
        validatePdfPageCatalog(catalog, catalog.documentId)
        require(first in 1..last && last <= catalog.pages.size)
        val response = request("POST", "/v1/documents/${catalog.documentId}/pdf-pages/selection",
            JSONObject().put("first_page", first).put("last_page", last).toString())
        fun integer(key: String): Int { val raw = response.get(key); require(raw is Int); return raw }
        val empty = response.getJSONArray("empty_pages")
        require(empty.length() <= catalog.pages.size)
        val emptyPages = (0 until empty.length()).map { val raw = empty.get(it); require(raw is Int); raw }
        val ids = response.getJSONArray("chapter_ids").strings()
        return validatePdfPageScope(PdfPageScope(response.getString("document_id"), integer("first_page"), integer("last_page"),
            ids, responseExcerpts(response), emptyPages), catalog, first, last, chapterIds)
    }
    fun searchDocumentSource(documentId: String, chapterIds: Set<String>, query: String): DocumentSearch {
        val response = request("POST", "/v1/documents/$documentId/search", JSONObject().put("chapter_ids", JSONArray(chapterIds.sorted())).put("query", query).put("limit", 20).toString())
        val matches = response.getJSONArray("matches")
        require(matches.length() <= 20)
        val hits = (0 until matches.length()).map { index ->
            val hit = matches.getJSONObject(index)
            fun integer(key: String): Int { val value = hit.get(key); require(value is Int); return value }
            val truncated = hit.get("context_truncated"); require(truncated is Boolean)
            SourceSearchHit(hit.getString("chapter_id"), hit.getString("title"), integer("start_character"), integer("end_character"),
                hit.getString("text"), integer("match_start"), integer("match_end"), truncated)
        }
        val more = response.get("has_more"); require(more is Boolean)
        return validateSourceSearch(DocumentSearch(response.getString("document_id"), response.getString("query"), chapterIds, hits, more),
            documentId, query, chapterIds, response.getString("match_mode"))
    }
    data class StartedDocumentQuiz(val id: String, val question: QuizQuestion, val total: Int, val difficulty: String?, val questionType: String?)
    fun createQuiz(documentId: String, chapterIds: List<String>, count: Int, difficulty: String, questionType: String, requestId: String, excerpts: List<DocumentExcerpt> = emptyList()): StartedDocumentQuiz {
        val body = JSONObject().put("chapter_ids", JSONArray(chapterIds)).put("question_count", count).put("difficulty", difficulty).put("question_type", questionType).put("request_id", requestId)
        if (excerpts.isNotEmpty()) body.put("source_ranges", excerptsJson(excerpts))
        val response = request("POST", "/v1/documents/$documentId/quizzes", body.toString())
        check(responseExcerpts(response) == canonicalExcerpts(excerpts)) { "Server did not confirm the requested excerpts" }
        val returnedType = if (response.isNull("question_type")) null else response.getString("question_type")
        validateDocumentFormat(questionType, returnedType)
        val first = question(response.getJSONObject("first_question"))
        validateDocumentOptions(returnedType, first.options)
        return StartedDocumentQuiz(response.getString("id"), first, response.getInt("question_count"), if (response.isNull("difficulty")) null else response.getString("difficulty"), returnedType)
    }
    data class ResumedDocumentQuiz(val document: StudyDocument, val total: Int, val question: QuizQuestion?, val feedback: Feedback?, val difficulty: String?, val questionType: String?, val excerpts: List<DocumentExcerpt> = emptyList())
    fun resumeDocumentQuiz(id: String): ResumedDocumentQuiz {
        val response = request("GET", "/v1/quizzes/$id", null)
        val feedback = response.optJSONObject("last_feedback")?.let { value -> Feedback(value.getBoolean("correct"), value.getString("selected_option"), value.getString("correct_option"), value.getString("explanation"), value.getString("source_reference"), value.optJSONObject("next_question")?.let(::question)) }
        val returnedType = if (response.isNull("question_type")) null else response.getString("question_type")
        require(returnedType == null || returnedType in documentQuestionTypes) { "Unsupported saved quiz format" }
        val pending = response.optJSONObject("question")?.let(::question)
        pending?.let { validateDocumentOptions(returnedType, it.options) }
        feedback?.next?.let { validateDocumentOptions(returnedType, it.options) }
        return ResumedDocumentQuiz(document(response.getJSONObject("document")), response.getInt("total"), pending, feedback, if (response.isNull("difficulty")) null else response.getString("difficulty"), returnedType, responseExcerpts(response))
    }
    fun answer(quizId: String, questionId: String, option: String): Feedback { val response = request("POST", "/v1/quizzes/$quizId/questions/$questionId/answer", JSONObject().put("selected_option", option).toString()); return Feedback(response.getBoolean("correct"), response.getString("selected_option"), response.getString("correct_option"), response.getString("explanation"), response.getString("source_reference"), response.optJSONObject("next_question")?.let(::question)) }
    fun results(quizId: String): Results { val response = request("GET", "/v1/quizzes/$quizId/results", null); return Results(response.getInt("answered"), response.getInt("total"), response.getInt("correct"), response.getDouble("accuracy").toFloat(), response.getJSONArray("mistakes").toQuestionList()) }
    data class StartedDiagnostic(val id: String, val question: DiagnosticQuestion, val ordinal: Int, val total: Int)
    data class DiagnosticResult(val correct: Boolean, val nextAction: String, val nextQuestion: DiagnosticQuestion?, val ordinal: Int, val masteryScore: Int, val tutor: TutorLesson?)
    data class RewriteResult(val mastered: Boolean, val score: Int, val confidence: String, val coaching: String?, val nextAction: String, val nextQuestion: DiagnosticQuestion?, val ordinal: Int?, val assessmentPoints: Int?, val assessmentFeedback: String?, val nextLesson: TutorLesson? = null)
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
    data class PracticeResult(val correct: Boolean, val nextLesson: TutorLesson?)
    fun submitPractice(sessionId: String, answer: String): PracticeResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/practice", JSONObject().put("response", answer).put("fresh_practice", true).toString())
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            PracticeResult(response.getBoolean("correct"), response.optJSONObject("next_practice")?.let {
                TutorLesson(it.getString("title"), it.getString("explanation"), it.getString("worked_example"), it.getString("hint"), it.getString("practice_prompt"))
            })
        }
    }
    fun submitRewrite(sessionId: String, rewrite: String): RewriteResult {
        val response = request("POST", "/v1/mastery/sessions/$sessionId/rewrite", JSONObject().put("response", rewrite).put("fresh_practice", true).toString())
        val next = response.optJSONObject("next_question")
        return masterySubmissionState.accept(sessionId, response.getString("state_token")) {
            RewriteResult(response.getBoolean("mastery_achieved"), (response.getDouble("mastery_score") * 100).toInt(),
            response.getString("confidence").replace('_', ' ').replaceFirstChar(Char::uppercase),
            if (response.isNull("coaching")) null else response.getString("coaching"), response.getString("next_action"),
            next?.let(::adaptiveQuestion), next?.getInt("ordinal"),
            if (response.isNull("assessment_points")) null else response.getInt("assessment_points"),
            if (response.isNull("assessment_feedback")) null else response.getString("assessment_feedback"),
            response.optJSONObject("next_practice")?.let {
                TutorLesson(it.getString("title"), it.getString("explanation"), it.getString("worked_example"), it.getString("hint"), it.getString("practice_prompt"))
            })
        }
    }
    fun progressDashboard(grade: Int, learnerId: String? = null): ProgressSnapshot {
        val path = learnerId?.let { "/v1/guardian/learners/$it/progress/dashboard?grade=$grade" } ?: "/v1/progress/dashboard?grade=$grade"
        val response = request("GET", path, null)
        val subjectsObject = response.getJSONObject("subjects")
        val subjects = subjectsObject.keys().asSequence().associateWith { (subjectsObject.getDouble(it) * 100).toInt() }
        val chapters = response.getJSONArray("chapters")
        val scores = (0 until chapters.length()).associate { index -> val item = chapters.getJSONObject(index); "${item.getString("subject_id")}:${item.getString("chapter_id")}" to (item.getDouble("mastery") * 100).toInt() }
        val mastered = (0 until chapters.length()).mapNotNull { index -> val item = chapters.getJSONObject(index); if (item.getString("status") == "mastered" && item.getDouble("mastery") >= 1.0) "${item.getString("subject_id")}:${item.getString("chapter_id")}" else null }.toSet()
        val unlocked = serverChapterUnlocks(grade, if (response.isNull("grade")) null else response.getInt("grade"),
            if (response.isNull("unlocked_chapter_ids")) null else response.getJSONArray("unlocked_chapter_ids").strings())
        return ProgressSnapshot(subjects, response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings(), chapterScores = scores, masteredChapterIds = mastered, unlockedChapterIds = unlocked)
    }
    fun weeklyReport(grade: Int, learnerId: String? = null): ProgressSnapshot {
        val path = learnerId?.let { "/v1/guardian/learners/$it/progress/weekly-report?grade=$grade" } ?: "/v1/progress/weekly-report?grade=$grade"
        val response = request("GET", path, null)
        val studySeconds = parseWeeklyStudySeconds(if (response.isNull("observed_study_seconds")) null else response.get("observed_study_seconds"))
        return ProgressSnapshot(emptyMap(), response.getJSONArray("weak_areas").strings(), response.getJSONArray("recommendations").strings(),
            response.getInt("questions_answered"), (response.getDouble("accuracy") * 100).toInt(), response.getInt("mastered_chapters"),
            response.getDouble("estimated_exam_readiness").toInt(), response.getString("readiness_label").replace('_', ' ').replaceFirstChar(Char::uppercase),
            weeklyObservedStudySeconds = studySeconds)
    }
    fun progressWithWeekly(grade: Int, learnerId: String? = null): ProgressSnapshot { val dashboard = progressDashboard(grade, learnerId); val weekly = weeklyReport(grade, learnerId); return dashboard.copy(questionsAnswered = weekly.questionsAnswered, accuracy = weekly.accuracy, masteredChapters = weekly.masteredChapters, examReadiness = weekly.examReadiness, readinessLabel = weekly.readinessLabel, weeklyObservedStudySeconds = weekly.weeklyObservedStudySeconds) }
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
    private fun requestArray(method: String, path: String): JSONArray {
        val active = connection(method, path, "application/json")
        return try { JSONArray(readApiResponse(active)) } finally { active.disconnect() }
    }
    private fun connection(method: String, path: String, contentType: String): HttpURLConnection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply { requestMethod = method; instanceFollowRedirects = false; connectTimeout = 15_000; readTimeout = apiReadTimeout(method, path); doInput = true; setRequestProperty("Content-Type", contentType); token?.let { setRequestProperty("Authorization", "Bearer $it") }; if (method == "POST" || method == "PUT" || method == "PATCH") doOutput = true }
    private fun readJson(connection: HttpURLConnection, authenticationRequest: Boolean = false): JSONObject = JSONObject(readApiResponse(connection, authenticationRequest))
    private fun document(value: JSONObject) = StudyDocument(value.getString("id"), value.getString("original_name"), value.getJSONArray("chapters").let { array -> (0 until array.length()).map { index -> array.getJSONObject(index).let { Chapter(it.getString("id"), it.getString("title"), it.getDouble("confidence").toFloat()) } } })
    private fun question(value: JSONObject): QuizQuestion {
        val options = value.getJSONArray("options").strings()
        validateDocumentOptions(if (value.isNull("question_type")) null else value.getString("question_type"), options)
        return QuizQuestion(value.getString("id"), value.getInt("ordinal"), value.getString("prompt"), options, value.getString("source_reference"))
    }
    private fun adaptiveQuestion(value: JSONObject) = DiagnosticQuestion(value.getString("prompt"), value.getJSONArray("options").strings(), "")
    private fun guardianAccount(value: JSONObject) = GuardianAccount(value.getString("id"), value.getString("email"), value.getString("linked_at"))
    private fun guardianAccounts(values: JSONArray) = (0 until values.length()).map { guardianAccount(values.getJSONObject(it)) }
    private fun JSONArray.toQuestionList(): List<QuizQuestion> = (0 until length()).map { question(getJSONObject(it)) }
    private fun JSONArray.strings(): List<String> = (0 until length()).map(::getString)
}
