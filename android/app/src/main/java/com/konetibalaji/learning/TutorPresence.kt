package com.konetibalaji.learning

enum class TutorPresence { READY, THINKING, SPEAKING }

fun tutorPresence(loading: Boolean, reading: Boolean): TutorPresence = when {
    loading -> TutorPresence.THINKING
    reading -> TutorPresence.SPEAKING
    else -> TutorPresence.READY
}
