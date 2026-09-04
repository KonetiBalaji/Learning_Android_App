package com.konetibalaji.learning

data class RetentionPolicy(val activeLearningData: String, val uploadedDocuments: String,
    val deletedFiles: String, val guardianInvitationDays: Int, val crashOrphanHours: Int,
    val backupDays: Int)

fun validateRetentionPolicy(value: RetentionPolicy): RetentionPolicy {
    require(value.activeLearningData == "until_account_deletion")
    require(value.uploadedDocuments == "until_document_or_account_deletion")
    require(value.deletedFiles == "queued_for_immediate_cleanup")
    require(value.guardianInvitationDays in 1..365 && value.crashOrphanHours in 1..720)
    require(value.backupDays in 1..365)
    return value
}
