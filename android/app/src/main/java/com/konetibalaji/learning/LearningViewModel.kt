package com.konetibalaji.learning

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
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

sealed interface Screen {
    data object SignIn : Screen
    data object Home : Screen
    data object Chapters : Screen
    data object Question : Screen
    data object Feedback : Screen
    data object Results : Screen
}

data class AppUiState(
    val screen: Screen = Screen.SignIn,
    val loading: Boolean = false,
    val error: String? = null,
    val document: StudyDocument? = null,
    val selectedChapterId: String? = null,
    val quizId: String? = null,
    val question: QuizQuestion? = null,
    val feedback: Feedback? = null,
    val results: Results? = null,
)

class LearningViewModel : ViewModel() {
    private val api = LearningApi()
    private val mutableState = MutableStateFlow(AppUiState())
    val state: StateFlow<AppUiState> = mutableState.asStateFlow()

    fun createAccount(email: String, password: String) = perform(Screen.Home) { api.register(email, password) }

    fun upload(context: Context, uri: Uri) = perform(Screen.Chapters) {
        val document = api.upload(context.contentResolver, uri)
        mutableState.value = mutableState.value.copy(document = document, selectedChapterId = document.chapters.firstOrNull()?.id)
    }

    fun selectChapter(chapterId: String) {
        mutableState.value = mutableState.value.copy(selectedChapterId = chapterId)
    }

    fun createQuiz() = perform(Screen.Question) {
        val current = mutableState.value
        val document = requireNotNull(current.document)
        val chapter = requireNotNull(current.selectedChapterId)
        val quiz = api.createQuiz(document.id, chapter)
        mutableState.value = current.copy(quizId = quiz.first, question = quiz.second, feedback = null, results = null)
    }

    fun submitAnswer(option: String) = perform(Screen.Feedback) {
        val current = mutableState.value
        val quizId = requireNotNull(current.quizId)
        val question = requireNotNull(current.question)
        mutableState.value = current.copy(feedback = api.answer(quizId, question.id, option))
    }

    fun continueAfterFeedback() {
        val current = mutableState.value
        val feedback = current.feedback ?: return
        if (feedback.next != null) {
            mutableState.value = current.copy(screen = Screen.Question, question = feedback.next, feedback = null)
        } else {
            loadResults()
        }
    }

    fun loadResults() = perform(Screen.Results) {
        val current = mutableState.value
        mutableState.value = current.copy(results = api.results(requireNotNull(current.quizId)))
    }

    fun startAnotherDocument() {
        mutableState.value = AppUiState(screen = Screen.Home)
    }

    fun clearError() {
        mutableState.value = mutableState.value.copy(error = null)
    }

    private fun perform(destination: Screen, block: suspend () -> Unit) {
        viewModelScope.launch {
            mutableState.value = mutableState.value.copy(loading = true, error = null)
            runCatching { withContext(Dispatchers.IO) { block() } }
                .onSuccess { mutableState.value = mutableState.value.copy(screen = destination, loading = false) }
                .onFailure { mutableState.value = mutableState.value.copy(loading = false, error = it.message ?: "Something went wrong. Please try again.") }
        }
    }
}

private class LearningApi {
    private var token: String? = null
    private val baseUrl = BuildConfig.API_BASE_URL

    fun register(email: String, password: String) {
        val body = JSONObject().put("email", email).put("password", password)
        token = request("POST", "/v1/auth/register", body.toString()).getString("access_token")
    }

    fun upload(resolver: ContentResolver, uri: Uri): StudyDocument {
        val displayName = resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            cursor.moveToFirst(); cursor.getString(cursor.getColumnIndexOrThrow(android.provider.OpenableColumns.DISPLAY_NAME))
        } ?: "study-material.txt"
        val bytes = resolver.openInputStream(uri)?.use { it.readBytes() } ?: error("The selected file could not be read")
        val boundary = "Learnly-${UUID.randomUUID()}"
        val connection = connection("POST", "/v1/documents", "multipart/form-data; boundary=$boundary")
        BufferedOutputStream(connection.outputStream).use { output ->
            output.write("--$boundary\r\n".toByteArray())
            output.write("Content-Disposition: form-data; name=\"file\"; filename=\"${displayName.replace("\"", "")}\"\r\n".toByteArray())
            output.write("Content-Type: ${resolver.getType(uri) ?: "application/octet-stream"}\r\n\r\n".toByteArray())
            output.write(bytes)
            output.write("\r\n--$boundary--\r\n".toByteArray())
        }
        return document(readJson(connection))
    }

    fun createQuiz(documentId: String, chapterId: String): Pair<String, QuizQuestion> {
        val body = JSONObject().put("chapter_ids", JSONArray().put(chapterId)).put("question_count", 10)
        val response = request("POST", "/v1/documents/$documentId/quizzes", body.toString())
        return response.getString("id") to question(response.getJSONObject("first_question"))
    }

    fun answer(quizId: String, questionId: String, option: String): Feedback {
        val response = request("POST", "/v1/quizzes/$quizId/questions/$questionId/answer", JSONObject().put("selected_option", option).toString())
        return Feedback(
            correct = response.getBoolean("correct"), selected = response.getString("selected_option"), answer = response.getString("correct_option"),
            explanation = response.getString("explanation"), source = response.getString("source_reference"),
            next = response.optJSONObject("next_question")?.let(::question),
        )
    }

    fun results(quizId: String): Results {
        val response = request("GET", "/v1/quizzes/$quizId/results", null)
        return Results(
            answered = response.getInt("answered"), total = response.getInt("total"), correct = response.getInt("correct"), accuracy = response.getDouble("accuracy").toFloat(),
            mistakes = response.getJSONArray("mistakes").toQuestionList(),
        )
    }

    private fun request(method: String, path: String, body: String?): JSONObject {
        val connection = connection(method, path, "application/json")
        if (body != null) connection.outputStream.use { it.write(body.toByteArray()) }
        return readJson(connection)
    }

    private fun connection(method: String, path: String, contentType: String): HttpURLConnection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
        requestMethod = method
        connectTimeout = 15_000
        readTimeout = 30_000
        doInput = true
        setRequestProperty("Content-Type", contentType)
        token?.let { setRequestProperty("Authorization", "Bearer $it") }
        if (method == "POST") doOutput = true
    }

    private fun readJson(connection: HttpURLConnection): JSONObject {
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (status !in 200..299) throw IllegalStateException(JSONObject(text.ifBlank { "{}" }).optString("detail", "Request failed ($status)"))
        return JSONObject(text)
    }

    private fun document(value: JSONObject): StudyDocument = StudyDocument(
        id = value.getString("id"), name = value.getString("original_name"),
        chapters = value.getJSONArray("chapters").let { array -> (0 until array.length()).map { index ->
            array.getJSONObject(index).let { Chapter(it.getString("id"), it.getString("title"), it.getDouble("confidence").toFloat()) }
        } },
    )

    private fun question(value: JSONObject): QuizQuestion = QuizQuestion(
        id = value.getString("id"), ordinal = value.getInt("ordinal"), prompt = value.getString("prompt"),
        options = value.getJSONArray("options").let { array -> (0 until array.length()).map(array::getString) }, sourceReference = value.getString("source_reference"),
    )

    private fun JSONArray.toQuestionList(): List<QuizQuestion> = (0 until length()).map { question(getJSONObject(it)) }
}
