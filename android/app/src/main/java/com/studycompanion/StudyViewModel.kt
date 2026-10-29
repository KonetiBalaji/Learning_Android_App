package com.studycompanion

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.studycompanion.data.ApiException
import com.studycompanion.data.SessionStore
import com.studycompanion.data.StudyRepository
import com.studycompanion.data.objects
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
    val aiMode: Boolean = false,
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

    fun openDocument(doc: JSONObject) { mutable.update { it.copy(document = doc, screen = "configure", error = null) } }

    fun upload(uri: Uri) = run {
        mutable.update { it.copy(uploadProgress = 0) }
        val document = repository.upload(uri) { amount -> mutable.update { it.copy(uploadProgress = amount) } }
        loadHome()
        mutable.update { it.copy(document = document, screen = "configure") }
    }

    fun deleteDocument(id: String) = run {
        repository.call("/documents/$id", "DELETE")
        session.activeQuiz = ""
        loadHome()
        mutable.update { it.copy(screen = "home", document = null, quiz = null, results = null) }
    }

    fun startQuiz(sectionIds: Set<String>, count: Int, kind: String, difficulty: String, first: String, last: String, topic: String) = run {
        val doc = state.value.document ?: return@run
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
        mutable.update { it.copy(document = doc) }
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

    fun showResults(id: String) = run {
        val quiz = JSONObject(repository.call("/quizzes/$id"))
        val doc = JSONObject(repository.call("/documents/${quiz.getString("document_id")}"))
        mutable.update { it.copy(document = doc) }
        acceptQuiz(quiz)
    }

    fun showSource(sourceId: String) = run {
        val documentId = state.value.document?.getString("id") ?: return@run
        val passage = JSONObject(repository.call("/documents/$documentId/passages/$sourceId"))
        mutable.update { it.copy(source = passage) }
    }
    fun hideSource() { mutable.update { it.copy(source = null) } }

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
