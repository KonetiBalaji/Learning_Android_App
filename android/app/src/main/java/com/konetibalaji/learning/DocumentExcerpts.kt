package com.konetibalaji.learning

import java.util.Base64
import org.json.JSONArray
import org.json.JSONObject

data class DocumentExcerpt(val chapterId: String, val start: Int, val end: Int)

fun canonicalExcerpts(values: List<DocumentExcerpt>): List<DocumentExcerpt> {
    require(values.size <= 50) { "Choose at most 50 excerpts" }
    val sorted = values.sortedWith(compareBy({ it.start }, { it.end }, { it.chapterId }))
    require(sorted.all { it.chapterId.isNotBlank() && it.start >= 0 && it.end > it.start }) { "Invalid excerpt boundaries" }
    require(sorted.zipWithNext().all { (left, right) -> left.end <= right.start }) { "Excerpts overlap or repeat. Clear the selection to replace them." }
    return sorted
}

fun excerptFromSelection(preview: DocumentPreview, first: Int, last: Int): DocumentExcerpt {
    val start = minOf(first, last)
    val end = maxOf(first, last)
    require(start >= 0 && end <= preview.text.length && start < end) { "Highlight some source text first" }
    fun boundary(index: Int) = index == 0 || index == preview.text.length ||
        !(preview.text[index - 1].isHighSurrogate() && preview.text[index].isLowSurrogate())
    require(boundary(start) && boundary(end)) { "Select complete characters" }
    require(preview.text.substring(start, end).isNotBlank()) { "Highlight text, not only spaces" }
    val absoluteStart = preview.start.toLong() + preview.text.codePointCount(0, start)
    val absoluteEnd = preview.start.toLong() + preview.text.codePointCount(0, end)
    require(absoluteEnd <= preview.end && absoluteStart >= 0)
    return DocumentExcerpt(preview.chapterId, absoluteStart.toInt(), absoluteEnd.toInt())
}

// Only IDs/offsets are persisted, never the highlighted source text.
fun encodeExcerpts(values: List<DocumentExcerpt>): String = canonicalExcerpts(values).joinToString(";") {
    "${Base64.getUrlEncoder().withoutPadding().encodeToString(it.chapterId.toByteArray(Charsets.UTF_8))},${it.start},${it.end}"
}

fun decodeExcerpts(saved: String?): List<DocumentExcerpt> {
    if (saved == null) return emptyList()
    require(saved.isNotEmpty() && saved.length <= 30000) { "Saved excerpt selection is invalid" }
    return canonicalExcerpts(saved.split(';').map {
        val parts = it.split(',')
        require(parts.size == 3) { "Saved excerpt selection is invalid" }
        DocumentExcerpt(String(Base64.getUrlDecoder().decode(parts[0]), Charsets.UTF_8), parts[1].toInt(), parts[2].toInt())
    })
}

fun excerptsJson(values: List<DocumentExcerpt>): JSONArray = JSONArray().apply {
    canonicalExcerpts(values).forEach { put(JSONObject().put("chapter_id", it.chapterId).put("start_character", it.start).put("end_character", it.end)) }
}

fun responseExcerpts(response: JSONObject): List<DocumentExcerpt> {
    if (response.isNull("source_ranges")) return emptyList()
    val values = response.getJSONArray("source_ranges")
    require(values.length() in 1..50) { "Invalid saved excerpt selection" }
    return canonicalExcerpts((0 until values.length()).map {
        val value = values.getJSONObject(it)
        val start = value.get("start_character")
        val end = value.get("end_character")
        require(start is Int && end is Int) { "Invalid excerpt offsets" }
        DocumentExcerpt(value.getString("chapter_id"), start, end)
    })
}
