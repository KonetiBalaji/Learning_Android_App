package com.studycompanion.data

import com.studycompanion.domain.OfflinePassage
import com.studycompanion.domain.OfflinePractice
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/** Local attempts remain untrusted until the server validates them on reconnection. */
class OfflineStudyRepository(private val cache: OfflineCache, private val session: SessionStore) {
    suspend fun open(id: String): JSONObject = cache.load(session.server, session.ownerId, id)
        ?: error("This offline copy expired or was removed. Save it again while online.")

    private suspend fun persist(bundle: JSONObject): JSONObject {
        cache.save(session.server, session.ownerId, bundle)
        return bundle
    }

    private fun copy(bundle: JSONObject) = JSONObject(bundle.toString())

    private suspend fun addQuiz(bundle: JSONObject, questions: JSONArray): JSONObject {
        val quizzes = bundle.optJSONArray("local_quizzes") ?: JSONArray()
        require(quizzes.length() < 20) { "This offline copy has 20 saved sessions. Removing the offline copy clears its local history, including unsynced answers." }
        quizzes.put(JSONObject().put("id", UUID.randomUUID().toString()).put("questions", questions)
            .put("index", 0).put("answers", JSONArray()).put("created", System.currentTimeMillis() / 1000.0)
            .put("selection", bundle.optJSONObject("last_selection") ?: JSONObject()).put("synced", false))
        bundle.put("local_quizzes", quizzes)
        return persist(bundle)
    }

    suspend fun create(id: String, sectionIds: Set<String>, first: Int?, last: Int?, count: Int, kind: String): JSONObject {
        val bundle = copy(open(id))
        require(!bundle.optBoolean("source_stale")) { "This saved source changed online. Save a current copy before starting more practice." }
        val document = bundle.getJSONObject("document")
        val sections = document.getJSONArray("sections").objects()
        require(sectionIds.all { id -> sections.any { it.getString("id") == id } }) { "A selected chapter no longer exists." }
        val expanded = sectionIds.toMutableSet()
        do {
            val before = expanded.size
            sections.filter { it.optString("parent_id") in expanded }.forEach { expanded.add(it.getString("id")) }
        } while (before != expanded.size)
        require((first == null) == (last == null)) { "Enter both first and last page." }
        if (first != null && last != null) require(document.getBoolean("has_real_pages") && first >= 1 && first <= last && last <= document.getInt("page_count")) { "Choose a valid PDF page range." }
        val passages = bundle.getJSONArray("passages").objects().filter {
            (expanded.isEmpty() || it.getString("section_id") in expanded) &&
                (first == null || it.getInt("page") in first..last!!)
        }.map { OfflinePassage(it.getString("id"), it.getString("section_id"), it.getInt("page"), it.getString("text")) }
        val questions = OfflinePractice.generate(passages, count, kind)
        val serialized = JSONArray(questions.map { q -> JSONObject().put("id", q.id).put("prompt", q.prompt)
            .put("choices", JSONArray(q.choices)).put("answer", q.answer).put("type", q.type)
            .put("source_id", q.source.id).put("section_id", q.source.sectionId).put("page", q.source.page)
            .put("quote", q.source.text).put("explanation", q.explanation).put("difficulty", "easy") })
        bundle.put("last_selection", JSONObject().put("section_ids", JSONArray(sectionIds.toList()))
            .put("page_start", first).put("page_end", last))
        return addQuiz(bundle, serialized)
    }

    suspend fun answer(id: String, quizId: String, index: Int, choice: Int): JSONObject {
        val bundle = copy(open(id))
        require(!bundle.optBoolean("source_stale")) { "This saved source changed online. Old sessions can only be reviewed." }
        val quiz = bundle.getJSONArray("local_quizzes").objects().first { it.getString("id") == quizId }
        require(index == quiz.getInt("index")) { "This question changed. Open the session again." }
        val question = quiz.getJSONArray("questions").getJSONObject(index)
        require(choice in 0 until question.getJSONArray("choices").length()) { "Choose a valid answer." }
        val answers = quiz.getJSONArray("answers")
        if (answers.length() > index) require(answers.getInt(index) == choice) { "This answer was already submitted." }
        else answers.put(choice)
        return persist(bundle)
    }

    suspend fun next(id: String, quizId: String, index: Int): JSONObject {
        val bundle = copy(open(id))
        require(!bundle.optBoolean("source_stale")) { "This saved source changed online. Old sessions can only be reviewed." }
        val quiz = bundle.getJSONArray("local_quizzes").objects().first { it.getString("id") == quizId }
        if (quiz.getInt("index") == index) {
            require(quiz.getJSONArray("answers").length() > index) { "Submit an answer first." }
            quiz.put("index", index + 1)
        }
        return persist(bundle)
    }

    suspend fun retry(id: String, quizId: String): JSONObject {
        val bundle = copy(open(id))
        require(!bundle.optBoolean("source_stale")) { "This saved source changed online. Old sessions can be reviewed but cannot start new practice." }
        val previous = bundle.getJSONArray("local_quizzes").objects().first { it.getString("id") == quizId }
        val questions = previous.getJSONArray("questions")
        require(previous.getInt("index") == questions.length()) { "Finish this session first." }
        val wrong = questions.objects().filterIndexed { index, question -> previous.getJSONArray("answers").getInt(index) != question.getInt("answer") }
        require(wrong.isNotEmpty()) { "No mistakes to retry." }
        bundle.put("last_selection", previous.optJSONObject("selection") ?: JSONObject())
        return addQuiz(bundle, JSONArray(wrong))
    }

    suspend fun reconcile(id: String, remote: JSONObject): JSONObject {
        val bundle = copy(open(id))
        val stale = remote.getString("source_fingerprint") != bundle.getString("source_fingerprint") || remote.getString("processing_state") != "ready"
        bundle.put("source_stale", stale)
        return persist(bundle)
    }

    suspend fun sync(id: String, api: StudyRepository): JSONObject {
        var bundle = reconcile(id, JSONObject(api.call("/documents/$id/offline-status")))
        require(!bundle.optBoolean("source_stale")) { "The saved source changed. Old sessions cannot be imported into current progress. Remove this copy before saving current material." }
        val sessions = bundle.optJSONArray("local_quizzes")?.objects().orEmpty()
        for (quiz in sessions) {
            val questions = quiz.getJSONArray("questions")
            if (quiz.optBoolean("synced") || quiz.getInt("index") < questions.length()) continue
            val body = JSONObject().put("local_id", quiz.getString("id")).put("source_fingerprint", bundle.getString("source_fingerprint"))
                .put("selection", quiz.optJSONObject("selection") ?: JSONObject())
                .put("questions", JSONArray(questions.objects().mapIndexed { index, q ->
                    JSONObject().put("source_id", q.getString("source_id")).put("prompt", q.getString("prompt"))
                        .put("choices", q.getJSONArray("choices")).put("type", q.getString("type"))
                        .put("selected", quiz.getJSONArray("answers").getInt(index))
                }))
            val saved = JSONObject(api.call("/documents/$id/offline-attempts", "POST", body))
            quiz.put("synced", true).put("server_id", saved.getString("id"))
            // Persist each acknowledgement; a lost acknowledgement is replayed with the same local ID.
            bundle = persist(bundle)
        }
        return bundle
    }
}
