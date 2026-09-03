package com.konetibalaji.learning

/** A repair may add ranges, but must never rewrite an existing selection. */
fun stateAfterStructureRepair(current: AppUiState, repaired: StudyDocument): AppUiState {
    val original = requireNotNull(current.document)
    require(repaired.id == original.id) { "Repair returned a different document" }
    val ids = repaired.chapters.map { it.id }
    require(ids.distinct().size == ids.size) { "Repair returned duplicate chapter IDs" }
    require(repaired.chapters.filter { it.id in original.chapters.map(Chapter::id) } == original.chapters) {
        "Repair changed existing chapters. Reopen the document to review its structure."
    }
    require(ids.containsAll(current.selectedChapterIds)) { "Repair did not preserve your selection" }
    val added = repaired.chapters.size - original.chapters.size
    return current.copy(document = repaired, documentRepairNotice = if (added == 0)
        "No omitted text ranges found. Your selection is unchanged."
    else "$added omitted text ranges added, not selected. Review them before adding them to your quiz.")
}
