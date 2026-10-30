package com.studycompanion

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.studycompanion.data.ApiException
import com.studycompanion.data.SessionStore
import com.studycompanion.data.StudyRepository
import com.studycompanion.data.objects
import com.studycompanion.data.strings
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
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
    val source: JSONObject? = null,
    val sourceDocument: JSONObject? = null,
    val aiMode: Boolean = false,
    val flashcards: List<JSONObject> = emptyList(),
    val dueOnly: Boolean = true,
    val ocrPages: List<JSONObject> = emptyList(),
    val ocrPage: JSONObject? = null,
    val studyConfig: JSONObject = JSONObject(),
    val searchSelection: JSONObject = JSONObject(),
    val searchQuery: String = "",
    val searchHits: List<JSONObject>? = null,
    val recommendation: JSONObject? = null,
    val tutorTurns: List<JSONObject> = emptyList(),
)

class StudyViewModel(application: Application) : AndroidViewModel(application) {
    val session = SessionStore(application)
    private val repository = StudyRepository(application, session)
    private val mutable = MutableStateFlow(StudyState(signedIn = session.token.isNotEmpty()))
    val state = mutable.asStateFlow()
    private var retryAction: (suspend () -> Unit)? = null

    init {
        if (state.value.signedIn) run {
            loadHome()
            val activeId = session.activeQuiz
            val active = state.value.progress?.optJSONArray("in_progress")?.objects()?.find { it.getString("id") == activeId }
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
                    session.token = ""
                    mutable.value = StudyState(error = "Your session expired. Sign in to continue.")
                } else mutable.update { it.copy(error = error.message ?: "Could not connect. Check your connection and retry.") }
            } finally { mutable.update { it.copy(busy = false, uploadProgress = null) } }
        }
    }

    fun retry() { retryAction?.let { run(it) } }
    fun dismissError() { mutable.update { it.copy(error = null) } }
    fun navigate(screen: String) { mutable.update { it.copy(screen = screen, error = null, source = null) } }

    fun authenticate(username: String, password: String, register: Boolean, server: String) = run {
        val parsed = Uri.parse(server)
        require(parsed.scheme in listOf("http", "https") && !parsed.host.isNullOrEmpty() && parsed.userInfo == null) { "Enter a valid server URL." }
        if (session.server != server.trim().trimEnd('/')) {
            session.token = ""
            session.activeQuiz = ""
        }
        session.server = server
        val reply = JSONObject(repository.call("/auth/${if (register) "register" else "login"}", "POST",
            JSONObject().put("username", username.trim()).put("password", password)))
        session.token = reply.getString("token")
        mutable.value = StudyState(signedIn = true, busy = true)
        loadHome()
    }

    private suspend fun loadHome() {
        val health = JSONObject(repository.call("/health"))
        val docs = JSONArray(repository.call("/documents")).objects()
        val progress = JSONObject(repository.call("/progress"))
        mutable.update { it.copy(documents = docs, progress = progress, aiMode = health.getString("generation_mode") == "openai") }
    }

    fun refresh() = run { loadHome() }

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

    private suspend fun loadOcrPage(pageNumber: Int? = null) {
        val document = state.value.document ?: return
        val id = document.getString("id")
        val pages = JSONArray(repository.call("/documents/$id/ocr-pages")).objects()
        val page = pages.find { it.getInt("page") == pageNumber } ?: pages.find { !it.getBoolean("reviewed") } ?: pages.firstOrNull()
        val detail = page?.let { JSONObject(repository.call("/documents/$id/ocr-pages/${it.getInt("page")}")) }
        mutable.update { it.copy(ocrPages = pages, ocrPage = detail, screen = "ocr", source = null) }
    }

    fun openOcrReview(pageNumber: Int? = null) = run { loadOcrPage(pageNumber) }

    fun confirmOcr(text: String) = run {
        val document = state.value.document ?: return@run
        val page = state.value.ocrPage ?: return@run
        val updated = JSONObject(repository.call("/documents/${document.getString("id")}/ocr-pages/${page.getInt("page")}/review", "POST", JSONObject().put("text", text)))
        mutable.update { it.copy(document = updated) }
        loadHome()
        if (updated.getString("processing_state") == "ready") mutable.update { it.copy(screen = "configure", ocrPage = null) }
        else loadOcrPage()
    }

    fun upload(uri: Uri) = run {
        mutable.update { it.copy(uploadProgress = 0) }
        val document = repository.upload(uri) { amount -> mutable.update { it.copy(uploadProgress = amount) } }
        loadHome()
        mutable.update { it.copy(document = document, screen = "configure", studyConfig = JSONObject(), searchSelection = JSONObject(), searchHits = null, quiz = null, results = null, recommendation = null) }
    }

    fun deleteDocument(id: String) = run {
        repository.call("/documents/$id", "DELETE")
        session.activeQuiz = ""
        loadHome()
        mutable.update { it.copy(screen = "home", document = null, quiz = null, results = null) }
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
        mutable.update { it.copy(quiz = quiz, screen = "quiz", results = null, source = null) }
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
        val same = document.getString("id") == state.value.document?.optString("id")
        mutable.update { it.copy(document = document, quiz = if (same) it.quiz else null, results = if (same) it.results else null,
            studyConfig = if (same) it.studyConfig else JSONObject(), searchSelection = if (same) it.searchSelection else JSONObject(), searchHits = if (same) it.searchHits else null) }
        loadOcrPage(source.getInt("page"))
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
            session.token = ""
            session.activeQuiz = ""
            mutable.value = StudyState()
        }
    }
    fun deleteAccount() = run {
        repository.call("/account", "DELETE")
        session.token = ""
        session.activeQuiz = ""
        mutable.value = StudyState()
    }
}
