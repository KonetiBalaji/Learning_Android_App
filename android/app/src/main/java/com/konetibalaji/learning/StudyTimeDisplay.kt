package com.konetibalaji.learning

fun parseWeeklyStudySeconds(value: Any?): Long? {
    if (value == null) return null
    require(value is Int || value is Long) { "Invalid recorded study time" }
    val seconds = (value as Number).toLong()
    require(seconds in 0..604_800) { "Recorded study time exceeds the report window" }
    return seconds
}

fun weeklyStudyTimeLabel(seconds: Long?): String = when {
    seconds == null -> "Unavailable"
    seconds == 0L -> "No recorded time"
    seconds < 60 -> "${seconds}s"
    seconds < 3600 -> "${seconds / 60}m ${seconds % 60}s"
    else -> "${seconds / 3600}h ${(seconds % 3600) / 60}m"
}
