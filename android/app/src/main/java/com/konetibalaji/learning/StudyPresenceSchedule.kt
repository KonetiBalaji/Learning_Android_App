package com.konetibalaji.learning

data class PresenceCommand(val sessionId: String, val reset: Boolean)

/** Monotonic local scheduling only; credited duration is calculated by the server. */
class StudyPresenceSchedule {
    private var session: String? = null
    private var sentAt: Long? = null
    fun reset() { session = null; sentAt = null }
    fun next(sessionId: String?, now: Long): PresenceCommand? {
        if (sessionId == null) { reset(); return null }
        val previous = sentAt
        val newInterval = session != sessionId || previous == null || now < previous || now - previous > 30_000
        if (!newInterval && now - requireNotNull(previous) < 15_000) return null
        session = sessionId
        sentAt = now
        return PresenceCommand(sessionId, newInterval)
    }
}

fun presenceEligible(foreground: Boolean, loading: Boolean, screen: Screen, now: Long, lastInteraction: Long): Boolean =
    foreground && !loading && now >= lastInteraction && now - lastInteraction <= 45_000 &&
        screen in setOf(Screen.Diagnostic, Screen.Tutor, Screen.Practice, Screen.Rewrite)
