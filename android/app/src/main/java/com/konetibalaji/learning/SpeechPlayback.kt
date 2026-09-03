package com.konetibalaji.learning

/** Main-thread queue identity: callbacks from cancelled/replaced audio are ignored. */
class SpeechPlayback {
    private var generation = 0L
    private val pending = mutableSetOf<String>()
    val active: Boolean get() = pending.isNotEmpty()

    fun begin(count: Int): List<String> {
        require(count > 0)
        generation++
        pending.clear()
        return List(count) { "lesson-$generation-$it" }.also { pending.addAll(it) }
    }

    fun complete(id: String?): Boolean = pending.remove(id) && pending.isEmpty()

    fun fail(id: String?): Boolean {
        if (id !in pending) return false
        pending.clear()
        return true
    }

    fun stop(): Boolean = active.also { pending.clear() }
}
