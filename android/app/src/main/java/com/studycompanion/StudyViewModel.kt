package com.studycompanion

import android.app.Application
import android.net.Uri
import androidx.core.net.toUri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.studycompanion.data.ApiException
import com.studycompanion.data.SessionStore
import com.studycompanion.data.StudyRepository
import com.studycompanion.data.OfflineCache
import com.studycompanion.data.OfflineStudyRepository
import com.studycompanion.data.objects
import com.studycompanion.data.strings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

data class StudyState(
    val signedIn: Boolean = false,
    val screen: String = "home",
    val busy: Boolean = false,
    val error: String? = null,
    val uploadProgress: Int? = null,
    val documents: List<JSONObject> = emptyList(),
    val document: JSONObject? = null,
    val quiz: JSONObject? = null,
    val results: JSONObject? = null,
    val progress: JSONObject? = null,
    val inProgress: List<JSONObject> = emptyList(),
    val source: JSONObject? = null,
    val sourceDocument: JSONObject? = null,
    val aiMode: Boolean = false,
    val flashcards: List<JSONObject> = emptyList(),
    val dueOnly: Boolean = true,
    val ocrPages: List<JSONObject> = emptyList(),
    val ocrPage: JSONObject? = null,
    val ocrDocument: JSONObject? = null,
    val ocrReturn: String = "configure",
    val studyConfig: JSONObject = JSONObject(),
    val searchSelection: JSONObject = JSONObject(),
    val searchQuery: String = "",
    val searchHits: List<JSONObject>? = null,
    val recommendation: JSONObject? = null,
    val tutorTurns: List<JSONObject> = emptyList(),
    val offlineDocuments: List<JSONObject> = emptyList(),
    val offlineBundle: JSONObject? = null,
    val offlineQuizId: String? = null,
    val curriculumChapters: List<JSONObject> = emptyList(),
    val curriculumLesson: JSONObject? = null,
    val readinessCheck: JSONObject? = null,
    val progressLinks: List<JSONObject> = emptyList(),
    val progressInvite: JSONObject? = null,
    val progressReport: JSONObject? = null,
    val progressReportId: String? = null,
)

class StudyViewModel internal constructor(application: Application, private val repository: StudyRepository) : AndroidViewModel(application) {
    constructor(application: Application) : this(application, StudyRepository(application, SessionStore(application)))

    val session = repository.session
    private val offlineCache = OfflineCache(application)
    private val offlineStudy = OfflineStudyRepository(offlineCache, session)
    private val mutable = MutableStateFlow(StudyState(signedIn = session.token.isNotEmpty()))
    val state = mutable.asStateFlow()
    private var retryAction: (suspend () -> Unit)? = null

    init {
        viewModelScope.launch {
            state.map { it.offlineBundle }.distinctUntilChanged().collectLatest { bundle ->
                if (bundle != null) {
                    val deadline = (bundle.getDouble("expires_at") * 1000).toLong()
                    while (true) {
                        val remaining = deadline - System.currentTimeMillis()
                        if (remaining <= 0) break
                        delay(remaining.coerceAtMost(1_000))
                    }
                    val id = bundle.getJSONObject("document").getString("id")
                    mutable.update {
                        if (it.offlineBundle !== bundle) it
                        else it.copy(offlineBundle = null, offlineQuizId = null,
                            offlineDocuments = it.offlineDocuments.filterNot { doc -> doc.getString("id") == id })
                    }
                }
            }
        }
        if (state.value.signedIn) run {
            loadHome()
            val activeId = session.activeQuiz
            val active = state.value.inProgress.find { it.getString("id") == activeId }
            if (active != null) {
                val doc = JSONObject(repository.call("/documents/${active.getString("document_id")}"))
                mutable.update { it.copy(document = doc) }
                acceptQuiz(active)
            }
        }
    }

    private fun run(action: suspend () -> Unit) {
        if (state.value.busy) return
        retryAction = action
        viewModelScope.launch {
            mutable.update { it.copy(busy = true, error = null) }
            try { action(); retryAction = null }
            catch (cancelled: CancellationException) { throw cancelled }
            catch (error: Exception) {
                if (error is ApiException && error.status == 401 && state.value.signedIn) {
                    clearSession()
                    mutable.value = StudyState(error = "Your session expired. Sign in to continue.")
                } else mutable.update { it.copy(error = error.message ?: "Could not connect. Check your connection and retry.") }
            } finally { mutable.update { it.copy(busy = false, uploadProgress = null) } }
        }
    }

    fun retry() { retryAction?.let { run(it) } }
    fun dismissError() { mutable.update { it.copy(error = null) } }
    fun navigate(screen: String) {
        mutable.update { it.copy(screen = screen, error = null, source = null, sourceDocument = null,
            ocrDocument = null, ocrPage = null, ocrPages = emptyList(),
            progressInvite = null, progressReport = null, progressReportId = null) }
    }

    fun back() {
        val current = state.value
        if (current.busy) return
        when (current.screen) {
            "ocr" -> navigate(current.ocrReturn)
            "progress-sharing" -> if (current.progressReport != null) showProgressSharing() else navigate("progress")
            "curriculum" -> when {
                current.readinessCheck != null -> closeReadiness()
                current.curriculumLesson != null -> closeCurriculumChapter()
                else -> navigate("home")
            }
            "search", "tutor", "quiz" -> navigate(if (current.document != null) "configure" else "home")
            "mistakes", "adaptive", "flashcards" -> navigate(if (current.results != null) "results" else "home")
            "offline" -> when {
                current.offlineQuizId != null -> resumeOffline(null)
                current.offlineBundle != null -> showOffline()
                else -> navigate("home")
            }
            else -> navigate("home")
        }
    }

    private suspend fun selectServer(server: String) {
        val parsed = server.trim().toUri()
        require(parsed.scheme in listOf("http", "https") && !parsed.host.isNullOrEmpty() &&
            parsed.userInfo == null && parsed.query == null && parsed.fragment == null) { "Enter a valid server URL." }
        if (session.server != server.trim().trimEnd('/')) {
            offlineCache.clear()
            session.ownerId = ""
            session.token = ""
            session.activeQuiz = ""
        }
        session.server = server
    }

    private suspend fun acceptSignIn(reply: JSONObject) {
        val ownerId = reply.getString("owner_id")
        if (session.ownerId != ownerId) offlineCache.clear()
        session.ownerId = ownerId
        session.token = reply.getString("token")
        mutable.value = StudyState(signedIn = true, busy = true)
        retryAction = { loadHome() }
        loadHome()
    }

    fun authenticate(username: String, password: String, register: Boolean, server: String) = run {
        selectServer(server)
        acceptSignIn(JSONObject(repository.call("/auth/${if (register) "register" else "login"}", "POST",
            JSONObject().put("username", username.trim()).put("password", password))))
    }

    fun signInWithGoogle(server: String, getToken: suspend (String, String) -> String?) = run {
        selectServer(server)
        val challenge = JSONObject(repository.call("/auth/google/challenge", "POST"))
        val token = getToken(challenge.getString("client_id"), challenge.getString("nonce")) ?: return@run
        acceptSignIn(JSONObject(repository.call("/auth/google", "POST", JSONObject().put("id_token", token))))
    }

    private suspend fun loadHome() {
        val identity = JSONObject(repository.call("/account")).getString("owner_id")
        if (session.ownerId.isNotEmpty() && session.ownerId != identity) {
            offlineCache.clear()
            session.activeQuiz = ""
            mutable.value = StudyState(signedIn = true, busy = true)
        }
        session.ownerId = identity
        val health = JSONObject(repository.call("/health"))
        val docs = JSONArray(repository.call("/documents")).objects()
        val progress = JSONObject(repository.call("/progress"))
        val remoteIds = docs.map { it.getString("id") }.toSet()
        for (cached in offlineCache.documents(session.server, session.ownerId)) {
            val id = cached.getString("id")
            if (id !in remoteIds) offlineCache.remove(session.server, session.ownerId, id)
            else offlineStudy.reconcile(id, JSONObject(repository.call("/documents/$id/offline-status")))
        }
        val savedDocuments = offlineCache.documents(session.server, session.ownerId)
        val currentId = state.value.offlineBundle?.getJSONObject("document")?.getString("id")
        val refreshed = if (currentId != null && currentId in savedDocuments.map { it.getString("id") }) offlineStudy.open(currentId) else null
        mutable.update {
            val activeExists = it.document?.optString("id")?.let { id -> id in remoteIds } != false
            val citedExists = it.sourceDocument?.optString("id")?.let { id -> id in remoteIds } != false
            val scanExists = it.ocrDocument?.optString("id")?.let { id -> id in remoteIds } != false
            val screen = when {
                !scanExists && it.screen == "ocr" -> "home"
                !activeExists && it.screen in setOf("configure", "quiz", "results", "mistakes", "search", "tutor", "adaptive") -> "home"
                else -> it.screen
            }
            it.copy(screen = screen, documents = docs, progress = progress,
                inProgress = progress.getJSONArray("in_progress").objects(), aiMode = health.getString("generation_mode") == "openai",
                document = if (activeExists) it.document else null, quiz = if (activeExists) it.quiz else null,
                results = if (activeExists) it.results else null, source = if (activeExists && citedExists) it.source else null,
                sourceDocument = if (citedExists) it.sourceDocument else null,
                searchHits = if (activeExists) it.searchHits else null,
                tutorTurns = if (activeExists) it.tutorTurns else emptyList(),
                recommendation = if (activeExists) it.recommendation else null,
                flashcards = it.flashcards.filter { card -> card.getString("document_id") in remoteIds },
                ocrDocument = if (scanExists) it.ocrDocument else null,
                ocrPage = if (scanExists) it.ocrPage else null,
                ocrPages = if (scanExists) it.ocrPages else emptyList(),
                offlineDocuments = savedDocuments, offlineBundle = refreshed, offlineQuizId = if (refreshed == null) null else it.offlineQuizId)
        }
    }

    private suspend fun loadProgressSharing() {
        val links = JSONArray(repository.call("/progress-sharing")).objects()
        mutable.update { it.copy(screen = "progress-sharing", progressLinks = links,
            progressReport = null, progressReportId = null) }
    }

    fun showProgressSharing() = run { loadProgressSharing() }

    fun inviteProgressViewer(role: String) = run {
        val invite = JSONObject(repository.call("/progress-sharing/invitations", "POST", JSONObject().put("role", role)))
        mutable.update { it.copy(progressInvite = invite.put("role", role)) }
    }

    fun cancelProgressInvite(role: String) = run {
        repository.call("/progress-sharing/invitations/$role", "DELETE")
        mutable.update { if (it.progressInvite?.optString("role") == role) it.copy(progressInvite = null) else it }
    }

    fun redeemProgressInvite(code: String) = run {
        repository.call("/progress-sharing/redeem", "POST", JSONObject().put("code", code))
        retryAction = { loadProgressSharing() }
        loadProgressSharing()
    }

    fun readSharedProgress(id: String) = run {
        try {
            val report = JSONObject(repository.call("/progress-sharing/$id/report"))
            mutable.update { it.copy(progressReport = report, progressReportId = id) }
        } catch (error: ApiException) {
            if (error.status != 404) throw error
            removeProgressLink(id)
            mutable.update { it.copy(error = "This shared report is no longer available.") }
        }
    }

    fun revokeProgressLink(id: String) = run {
        repository.call("/progress-sharing/$id", "DELETE")
        removeProgressLink(id)
    }

    private fun removeProgressLink(id: String) {
        mutable.update { it.copy(progressLinks = it.progressLinks.filterNot { link -> link.getString("id") == id },
            progressReport = null, progressReportId = null) }
    }

    fun showCurriculum() = run {
        val chapters = JSONArray(repository.call("/curriculum")).objects()
        mutable.update { it.copy(screen = "curriculum", curriculumChapters = chapters, curriculumLesson = null, readinessCheck = null) }
    }

    fun openReadiness(assessment: String = "grade6-math") = run {
        val check = JSONObject(repository.call("/curriculum/readiness/$assessment", "POST"))
        mutable.update { it.copy(readinessCheck = check) }
    }

    fun answerReadiness(choice: Int) {
        val check = state.value.readinessCheck ?: return
        val assessment = check.getString("id")
        val response = JSONObject().put("index", check.getInt("index")).put("choice", choice)
        run {
            val next = JSONObject(repository.call("/curriculum/readiness/$assessment/answers", "POST", response))
            mutable.update { it.copy(readinessCheck = next) }
        }
    }

    fun closeReadiness() {
        mutable.update { it.copy(readinessCheck = null) }
    }

    fun openCurriculumChapter(id: String) = run {
        val lesson = JSONObject(repository.call("/curriculum/$id/lesson", "POST"))
        mutable.update { it.copy(curriculumLesson = lesson) }
    }

    fun closeCurriculumChapter() {
        mutable.update { it.copy(curriculumLesson = null) }
        run {
            val chapters = JSONArray(repository.call("/curriculum")).objects()
            mutable.update { it.copy(curriculumChapters = chapters) }
        }
    }

    fun answerCurriculum(action: String, choice: Int? = null, response: String = "") {
        val current = state.value.curriculumLesson ?: return
        val id = current.getString("chapter_id")
        val body = JSONObject().put("action", action).put("version", current.getInt("version"))
            .put("response", response).apply { if (choice != null) put("choice", choice) }
        run {
            val lesson = JSONObject(repository.call("/curriculum/$id/lesson/actions", "POST", body))
            val chapters = if (lesson.getString("phase") == "mastered") JSONArray(repository.call("/curriculum")).objects()
                else state.value.curriculumChapters
            mutable.update { it.copy(curriculumLesson = lesson, curriculumChapters = chapters) }
        }
    }

    fun refresh() = run { loadHome() }

    fun saveOffline() = run {
        val document = state.value.document ?: return@run
        val bundle = JSONObject(repository.call("/documents/${document.getString("id")}/offline-bundle"))
        val previous = offlineCache.load(session.server, session.ownerId, document.getString("id"))
        if (previous != null && previous.has("local_quizzes")) {
            require(previous.getString("source_fingerprint") == bundle.getString("source_fingerprint")) { "The source changed. Sync or remove the old offline copy before replacing its saved sessions." }
            bundle.put("local_quizzes", previous.getJSONArray("local_quizzes"))
        }
        offlineCache.save(session.server, session.ownerId, bundle)
        loadOfflineLibrary()
    }

    private suspend fun loadOfflineLibrary() {
        val documents = if (session.ownerId.isBlank()) emptyList() else offlineCache.documents(session.server, session.ownerId)
        mutable.update { it.copy(screen = "offline", offlineDocuments = documents, offlineBundle = null, offlineQuizId = null, source = null) }
    }

    fun showOffline() = run { loadOfflineLibrary() }
    fun openOffline(id: String) = run {
        val bundle = offlineStudy.open(id)
        mutable.update { it.copy(screen = "offline", offlineBundle = bundle, offlineQuizId = null) }
    }
    fun removeOffline(id: String) = run {
        offlineCache.remove(session.server, session.ownerId, id)
        loadOfflineLibrary()
    }
    fun syncOffline() = run {
        val id = offlineDocumentId()
        try {
            val bundle = offlineStudy.sync(id, repository)
            mutable.update { it.copy(offlineBundle = bundle) }
            loadHome()
        } catch (error: Exception) {
            if (error is ApiException && error.status == 404) {
                offlineCache.remove(session.server, session.ownerId, id)
                loadOfflineLibrary()
            } else {
                val bundle = offlineStudy.open(id)
                mutable.update { it.copy(offlineBundle = bundle) }
            }
            throw error
        }
    }
    fun resumeOffline(id: String?) { mutable.update { it.copy(offlineQuizId = id) } }
    private fun offlineDocumentId() = state.value.offlineBundle!!.getJSONObject("document").getString("id")
    fun startOffline(ids: Set<String>, first: String, last: String, count: Int, kind: String) = run {
        require(first.isBlank() || first.toIntOrNull() != null) { "Enter a valid first page." }
        require(last.isBlank() || last.toIntOrNull() != null) { "Enter a valid last page." }
        val bundle = offlineStudy.create(offlineDocumentId(), ids, first.toIntOrNull(), last.toIntOrNull(), count, kind)
        mutable.update { it.copy(offlineBundle = bundle, offlineQuizId = bundle.getJSONArray("local_quizzes").objects().last().getString("id")) }
    }
    fun answerOffline(choice: Int) = run {
        val quiz = state.value.offlineBundle!!.getJSONArray("local_quizzes").objects().first { it.getString("id") == state.value.offlineQuizId }
        val bundle = offlineStudy.answer(offlineDocumentId(), quiz.getString("id"), quiz.getInt("index"), choice)
        mutable.update { it.copy(offlineBundle = bundle) }
    }
    fun nextOffline() = run {
        val quiz = state.value.offlineBundle!!.getJSONArray("local_quizzes").objects().first { it.getString("id") == state.value.offlineQuizId }
        val bundle = offlineStudy.next(offlineDocumentId(), quiz.getString("id"), quiz.getInt("index"))
        mutable.update { it.copy(offlineBundle = bundle) }
    }
    fun retryOffline() = run {
        val bundle = offlineStudy.retry(offlineDocumentId(), state.value.offlineQuizId!!)
        mutable.update { it.copy(offlineBundle = bundle, offlineQuizId = bundle.getJSONArray("local_quizzes").objects().last().getString("id")) }
    }

    private fun setDocumentContext(document: JSONObject) {
        mutable.update { current ->
            if (current.document?.optString("id") == document.getString("id")) current.copy(document = document)
            else current.copy(document = document, studyConfig = JSONObject(), searchSelection = JSONObject(), searchHits = null, recommendation = null)
        }
    }

    fun openDocument(doc: JSONObject) { mutable.update {
        val sameDocument = it.document?.optString("id") == doc.getString("id")
        it.copy(document = doc, screen = "configure", error = null, studyConfig = JSONObject(), searchSelection = JSONObject(), searchHits = null,
            quiz = if (sameDocument) it.quiz else null, results = if (sameDocument) it.results else null, recommendation = null)
    } }

    private fun configuration(ids: Set<String>, count: Int, kind: String, difficulty: String, first: String, last: String, topic: String) =
        JSONObject().put("section_ids", JSONArray(ids.toList())).put("count", count.toString()).put("kind", kind).put("difficulty", difficulty)
            .put("first", first).put("last", last).put("topic", topic)

    fun openSearch(ids: Set<String>, count: Int, kind: String, difficulty: String, first: String, last: String, topic: String) {
        val selection = JSONObject().put("section_ids", JSONArray(ids.toList()))
        if (first.isNotBlank() || last.isNotBlank()) {
            val start = first.toIntOrNull()
            val end = last.toIntOrNull()
            if (start == null || end == null) {
                mutable.update { it.copy(error = "Enter a valid first and last page before searching.") }
                return
            }
            selection.put("page_start", start).put("page_end", end)
        }
        mutable.update { it.copy(screen = "search", searchSelection = selection, searchQuery = topic, searchHits = null,
            studyConfig = configuration(ids, count, kind, difficulty, first, last, topic)) }
    }

    fun search(query: String) = run {
        val doc = state.value.document ?: return@run
        val response = JSONObject(repository.call("/documents/${doc.getString("id")}/search", "POST",
            JSONObject().put("query", query.trim()).put("selection", state.value.searchSelection)))
        mutable.update { it.copy(searchQuery = query.trim(), searchHits = response.getJSONArray("hits").objects()) }
    }

    fun practiceSearchTopic() {
        val config = JSONObject(state.value.studyConfig.toString()).put("topic", state.value.searchQuery)
        mutable.update { it.copy(studyConfig = config, screen = "configure") }
    }

    fun openTutor(ids: Set<String>, count: Int, kind: String, difficulty: String, first: String, last: String, topic: String) {
        openSearch(ids, count, kind, difficulty, first, last, topic)
        if (state.value.screen != "search") return
        mutable.update { it.copy(screen = "tutor", tutorTurns = emptyList()) }
        run {
            val doc = state.value.document ?: return@run
            val turns = JSONArray(repository.call("/documents/${doc.getString("id")}/tutor")).objects()
            mutable.update { it.copy(tutorTurns = turns) }
        }
    }

    fun askTutor(question: String) {
        val docId = state.value.document?.getString("id") ?: return
        val body = JSONObject().put("question", question.trim()).put("selection", state.value.searchSelection)
            .put("request_id", java.util.UUID.randomUUID().toString())
        run {
            val turn = JSONObject(repository.call("/documents/$docId/tutor", "POST", body))
            mutable.update { current -> current.copy(tutorTurns = current.tutorTurns.filter { it.getString("id") != turn.getString("id") } + turn) }
        }
    }

    private suspend fun loadOcrPage(document: JSONObject, returnScreen: String, pageNumber: Int? = null) {
        val id = document.getString("id")
        val pages = JSONArray(repository.call("/documents/$id/ocr-pages")).objects()
        val page = pages.find { it.getInt("page") == pageNumber } ?: pages.find { !it.getBoolean("reviewed") } ?: pages.firstOrNull()
        val detail = page?.let { JSONObject(repository.call("/documents/$id/ocr-pages/${it.getInt("page")}")) }
        mutable.update { it.copy(ocrPages = pages, ocrPage = detail, ocrDocument = document, ocrReturn = returnScreen,
            screen = "ocr", source = null, sourceDocument = null) }
    }

    fun openOcrReview(pageNumber: Int? = null) = run {
        val current = state.value
        val document = (if (current.screen == "ocr") current.ocrDocument else current.document) ?: return@run
        loadOcrPage(document, if (current.screen == "ocr") current.ocrReturn else "configure", pageNumber)
    }

    fun confirmOcr(text: String) = run {
        val document = state.value.ocrDocument ?: return@run
        val page = state.value.ocrPage ?: return@run
        val updated = JSONObject(repository.call("/documents/${document.getString("id")}/ocr-pages/${page.getInt("page")}/review", "POST", JSONObject().put("text", text)))
        mutable.update { it.copy(document = if (it.document?.optString("id") == updated.getString("id")) updated else it.document,
            ocrDocument = updated) }
        loadHome()
        val returnScreen = state.value.ocrReturn
        if (updated.getString("processing_state") == "ready") {
            mutable.update { it.copy(screen = returnScreen, ocrPage = null, ocrDocument = null, ocrPages = emptyList()) }
        } else loadOcrPage(updated, returnScreen)
    }

    fun upload(uri: Uri) {
        var uploaded: JSONObject? = null
        run {
            val document = uploaded ?: kotlin.run {
                mutable.update { it.copy(uploadProgress = 0) }
                repository.upload(uri) { amount -> mutable.update { it.copy(uploadProgress = amount) } }
                    .also { uploaded = it }
            }
            loadHome()
            mutable.update { it.copy(document = document, screen = "configure", studyConfig = JSONObject(), searchSelection = JSONObject(), searchHits = null, quiz = null, results = null, recommendation = null) }
        }
    }

    fun deleteDocument(id: String) = run {
        repository.call("/documents/$id", "DELETE")
        if (session.ownerId.isNotBlank()) offlineCache.remove(session.server, session.ownerId, id)
        session.activeQuiz = ""
        loadHome()
        mutable.update { it.copy(screen = "home", document = null, quiz = null, results = null, source = null,
            offlineBundle = null, offlineQuizId = null, offlineDocuments = it.offlineDocuments.filterNot { doc -> doc.getString("id") == id }) }
    }

    fun startQuiz(sectionIds: Set<String>, count: Int, kind: String, difficulty: String, first: String, last: String, topic: String) = run {
        val doc = state.value.document ?: return@run
        mutable.update { it.copy(studyConfig = configuration(sectionIds, count, kind, difficulty, first, last, topic)) }
        val selection = JSONObject().put("section_ids", JSONArray(sectionIds.toList())).put("topic", topic.trim())
        if (first.isNotBlank() || last.isNotBlank()) {
            require(first.toIntOrNull() != null && last.toIntOrNull() != null) { "Enter a valid first and last page." }
            selection.put("page_start", first.toInt()).put("page_end", last.toInt())
        }
        acceptQuiz(JSONObject(repository.call("/documents/${doc.getString("id")}/quizzes", "POST",
            JSONObject().put("selection", selection).put("count", count).put("question_type", kind).put("difficulty", difficulty))))
    }

    private suspend fun acceptQuiz(quiz: JSONObject) {
        session.activeQuiz = quiz.getString("id")
        mutable.update {
            val otherAttempts = it.inProgress.filterNot { attempt -> attempt.getString("id") == quiz.getString("id") }
            val inProgress = if (quiz.getBoolean("complete")) otherAttempts else listOf(quiz) + otherAttempts
            it.copy(quiz = quiz, screen = "quiz", results = null, source = null, inProgress = inProgress)
        }
        mutable.update { current -> current.copy(document = current.document?.let { JSONObject(it.toString()).put("source_locked", true) }) }
        if (quiz.getBoolean("complete")) {
            val results = JSONObject(repository.call("/quizzes/${quiz.getString("id")}/results"))
            mutable.update { it.copy(results = results, screen = "results") }
            session.activeQuiz = ""
            loadHome()
        }
    }

    fun resume(id: String) = run {
        val quiz = JSONObject(repository.call("/quizzes/$id"))
        val doc = JSONObject(repository.call("/documents/${quiz.getString("document_id")}"))
        setDocumentContext(doc)
        acceptQuiz(quiz)
    }

    fun answer(choice: Int) = run {
        val quiz = state.value.quiz ?: return@run
        acceptQuiz(JSONObject(repository.call("/quizzes/${quiz.getString("id")}/answers", "POST",
            JSONObject().put("question_id", quiz.getJSONObject("question").getString("id")).put("choice", choice))))
    }

    fun next() = run {
        val quiz = state.value.quiz ?: return@run
        acceptQuiz(JSONObject(repository.call("/quizzes/${quiz.getString("id")}/next", "POST", JSONObject().put("expected_index", quiz.getInt("index")))))
    }

    fun retryMistakes() = run {
        val quiz = state.value.quiz ?: return@run
        acceptQuiz(JSONObject(repository.call("/quizzes/${quiz.getString("id")}/retry", "POST")))
    }

    fun recommendPractice() = run {
        val id = state.value.document?.getString("id") ?: return@run
        val advice = JSONObject(repository.call("/documents/$id/next-practice"))
        mutable.update { it.copy(recommendation = advice, screen = "adaptive") }
    }

    fun startRecommendedPractice() {
        val advice = state.value.recommendation ?: return
        startQuiz(advice.getJSONArray("section_ids").strings().toSet(), advice.getInt("count"), advice.getString("question_type"), advice.getString("difficulty"), "", "", "")
    }

    fun showResults(id: String) = run {
        val quiz = JSONObject(repository.call("/quizzes/$id"))
        val doc = JSONObject(repository.call("/documents/${quiz.getString("document_id")}"))
        setDocumentContext(doc)
        acceptQuiz(quiz)
    }

    fun showSource(sourceId: String) = run {
        val documentId = state.value.document?.getString("id") ?: return@run
        val passage = JSONObject(repository.call("/documents/$documentId/passages/$sourceId"))
        mutable.update { it.copy(source = passage, sourceDocument = it.document) }
    }
    fun hideSource() { mutable.update { it.copy(source = null, sourceDocument = null) } }

    fun openOriginalScan() = run {
        val source = state.value.source ?: return@run
        val document = state.value.sourceDocument ?: state.value.document ?: return@run
        loadOcrPage(document, state.value.screen, source.getInt("page"))
    }

    private suspend fun loadCards(dueOnly: Boolean) {
        val cards = JSONArray(repository.call("/flashcards?due_only=$dueOnly")).objects()
        mutable.update { it.copy(flashcards = cards, dueOnly = dueOnly, screen = "flashcards") }
    }

    fun showFlashcards(dueOnly: Boolean = true) = run { loadCards(dueOnly) }

    fun makeFlashcards(mistakesOnly: Boolean = false) = run {
        val quiz = state.value.quiz ?: return@run
        repository.call("/quizzes/${quiz.getString("id")}/flashcards", "POST", JSONObject().put("mistakes_only", mistakesOnly))
        loadCards(true)
    }

    fun rateFlashcard(card: JSONObject, quality: Int) {
        val requestId = java.util.UUID.randomUUID().toString()
        val version = card.getJSONObject("review").getInt("version")
        run {
            repository.call("/flashcards/${card.getString("id")}/reviews", "POST",
                JSONObject().put("quality", quality).put("expected_version", version).put("request_id", requestId))
            loadCards(state.value.dueOnly)
        }
    }

    fun showCardSource(card: JSONObject) = run {
        val documentId = card.getString("document_id")
        val document = JSONObject(repository.call("/documents/$documentId"))
        val source = JSONObject(repository.call("/documents/$documentId/passages/${card.getString("source_id")}"))
        mutable.update { it.copy(sourceDocument = document, source = source) }
    }

    fun signOut() = run {
        try { repository.call("/auth/session", "DELETE") }
        finally {
            clearSession()
        }
    }
    fun deleteAccount() = run {
        repository.call("/account", "DELETE")
        clearSession()
    }

    private suspend fun clearSession() {
        retryAction = null
        try { offlineCache.clear() }
        finally {
            session.ownerId = ""
            session.token = ""
            session.activeQuiz = ""
            mutable.value = StudyState()
        }
    }
}
