package com.konetibalaji.learning

private val supportedBadgeIds = setOf(
    "first_answer", "learn_from_mistakes", "chapter_master", "four_subject_explorer")

fun validateLearningBadge(value: LearningBadge): LearningBadge {
    require(value.id in supportedBadgeIds)
    require(value.title.isNotBlank() && value.title.length <= 80)
    require(value.description.isNotBlank() && value.description.length <= 180)
    require(value.earnedAt.isNotBlank() && value.earnedAt.length <= 50)
    return value
}
