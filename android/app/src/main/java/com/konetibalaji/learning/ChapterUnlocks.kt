package com.konetibalaji.learning

/** Legacy responses grant no new access; an explicitly wrong grade is rejected. */
fun serverChapterUnlocks(requestedGrade: Int, returnedGrade: Int?, ids: List<String>?): Set<String> {
    if (returnedGrade == null) return emptySet()
    require(returnedGrade == requestedGrade) { "Progress belongs to a different grade" }
    if (ids == null) return emptySet()
    require(ids.distinct().size == ids.size && ids.all { it.matches(Regex("[a-z][a-z0-9-]*:[a-z][a-z0-9-]*")) }) {
        "Invalid chapter unlock response"
    }
    return ids.toSet()
}
