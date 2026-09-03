package com.konetibalaji.learning

val availableInterests = listOf("sports", "music", "art", "nature", "space", "games")

fun toggleInterest(selected: List<String>, interest: String): List<String> = when {
    interest !in availableInterests -> selected
    interest in selected -> selected - interest
    selected.size < 3 -> selected + interest
    else -> selected
}
