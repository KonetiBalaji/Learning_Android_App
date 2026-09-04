package com.konetibalaji.learning

import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

data class GuardianAccessEvent(
    val id: String,
    val guardianId: String?,
    val guardianEmail: String?,
    val eventType: String,
    val occurredAt: String,
)

fun guardianAccessEventDescription(eventType: String): String = when (eventType) {
    "granted" -> "Report access granted"
    "revoked_by_learner" -> "You revoked report access"
    "revoked_by_guardian" -> "Parent or teacher removed access"
    else -> "Report access changed"
}

fun guardianAccessAccountLabel(event: GuardianAccessEvent): String =
    event.guardianEmail?.takeIf { it.isNotBlank() } ?: "Deleted account"

fun guardianAccessOccurredLabel(value: String): String = runCatching {
    OffsetDateTime.parse(value).format(DateTimeFormatter.ofPattern("MMM d, yyyy · h:mm a", Locale.US))
}.getOrElse { "Time unavailable" }
