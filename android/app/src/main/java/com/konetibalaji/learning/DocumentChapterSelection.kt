package com.konetibalaji.learning

/** Preserve explicit clearing and never silently replace an invalid selection. */
fun restoredChapterSelection(saved: Set<String>?, available: List<String>): Set<String> =
    if (saved == null) available.take(1).toSet()
    else if (!available.containsAll(saved)) emptySet()
    else available.filter { it in saved }.toSet()
